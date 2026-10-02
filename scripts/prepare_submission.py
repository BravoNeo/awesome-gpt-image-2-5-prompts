"""Parse maintainer-approved issue data; never execute issue text or download URLs."""
import json
import os
import re
import urllib.request
from pathlib import Path
from catalog import load_entries, stable_id, validate_entries

FIELDS = ['Title (English)', 'Title (Chinese, optional)', 'Description (English)', 'Description (Chinese, optional)', 'Original prompt', 'Original language', 'Translations JSON (optional)', 'Author name', 'Author handle (optional)', 'Original post URL', 'Model', 'Prompt kind', 'Reference input requirement', 'Media JSON', 'Categories JSON', 'Tags JSON (optional)', 'Contribution permission']


def parse_issue(body):
    # Only known headings are delimiters, so Markdown headings inside prompts survive.
    pattern = r'^### (' + '|'.join(re.escape(f) for f in FIELDS) + r')\s*$'
    matches = list(re.finditer(pattern, body, re.MULTILINE))
    values = {}
    for i, match in enumerate(matches):
        key = match.group(1)
        if key in values:
            raise ValueError('Duplicate form heading')
        value = body[match.end():matches[i+1].start() if i+1<len(matches) else len(body)].strip()
        values[key] = '' if value == '_No response_' else value
    if set(values) != set(FIELDS):
        raise ValueError('Use the submission form; missing or unknown fields')
    def structured(key, default=None):
        value = values[key]
        if not value and default is not None:
            return default
        return json.loads(value)
    if '- [x] I have permission to contribute this prompt and these media links.' not in values['Contribution permission']:
        raise ValueError('Contribution permission must be checked')
    source = values['Original post URL']
    title = {'en':values['Title (English)']}
    description = {'en':values['Description (English)']}
    for field,key,obj in [('Title (Chinese, optional)','zh',title),('Description (Chinese, optional)','zh',description)]:
        if values[field]:
            obj[key] = values[field]
    author = {'name':values['Author name']}
    if values['Author handle (optional)']:
        author['handle'] = values['Author handle (optional)']
    return {'id':stable_id(source),'slug':stable_id(source),'modelClaimed':values['Model'], 'title':title,'description':description,'author':author,'sourceUrl':source,'originalLanguage':values['Original language'],'originalPrompt':values['Original prompt'], 'translations':structured('Translations JSON (optional)',{}),'promptKind':values['Prompt kind'],'inputRequirement':values['Reference input requirement'], 'media':structured('Media JSON'),'categories':structured('Categories JSON'),'tags':structured('Tags JSON (optional)',[]),'rights':{'basis':'submitter-permission','note':'Submitter confirmed permission to contribute the prompt and media links. Original ownership remains with the author.'}}


def api(path):
    # Path is built solely from the repository event metadata and numeric issue ID.
    req = urllib.request.Request('https://api.github.com/' + path, headers={'Authorization':'Bearer '+os.environ['GH_TOKEN'], 'Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28','User-Agent':'prompt-submission-workflow'})
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.load(response)


def main():
    event = json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text())
    if event.get('action') != 'labeled' or event.get('label',{}).get('name') != 'approved':
        raise ValueError('Expected approved label event')
    repo = os.environ['GITHUB_REPOSITORY']
    sender = event['sender']['login']
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',repo) or not re.fullmatch(r'[A-Za-z0-9-]+',sender):
        raise ValueError('Invalid repository or actor')
    permission = api(f'repos/{repo}/collaborators/{sender}/permission')['permission']
    if permission not in {'write','maintain','admin'}:
        raise ValueError('Only maintainers may prepare approved submissions')
    issue_id = int(event['issue']['number'])
    issue = api(f'repos/{repo}/issues/{issue_id}')
    if issue.get('pull_request') or issue['state'] != 'open' or 'approved' not in [label['name'] for label in issue['labels']]:
        raise ValueError('Issue is not an open approved submission')
    entry = parse_issue(issue['body'] or '')
    validate_entries(load_entries()+[entry])
    target = Path('pending')
    target.mkdir(exist_ok=True)
    (target/(entry['id']+'.json')).write_text(json.dumps(entry,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Prepared one pending JSON file. A maintainer must review and commit it through a pull request.')


if __name__ == '__main__':
    main()
