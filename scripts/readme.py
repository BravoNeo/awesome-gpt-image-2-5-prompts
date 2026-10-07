"""README presentation helpers; never rewrite original prompts or catalog data."""
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def presentation():
    return json.loads((ROOT / 'docs/readme-presentation.json').read_text(encoding='utf-8'))


def template(part, locale, entries):
    value = (ROOT / f'docs/readme-{part}.{locale}.md').read_text(encoding='utf-8')
    creators = len({e['author']['handle'] for e in entries})
    return value.replace('{{count}}', str(len(entries))).replace('{{creators}}', str(creators)).rstrip()


def featured_entries(entries):
    chosen = presentation()['featured']
    by_slug = {e['slug']: e for e in entries}
    return [by_slug[s] for s in chosen if s in by_slug] + [e for e in entries if e['slug'] not in chosen]


def featured_navigation(entries, locale):
    zh = locale == 'zh'
    config = presentation()
    selected = [e for e in featured_entries(entries) if e['slug'] in config['featured']]
    rows = ['## ' + ('从这些作品开始' if zh else 'Start with these examples'), '',
            '| ' + ('作品 | 看点 |' if zh else 'Example | What to explore |'), '| --- | --- |']
    for e in selected:
        title = e['title'].get(locale) or e['title']['en']
        title = html.escape(title).replace('|', '&#124;')
        description = config.get('descriptions', {}).get(e['slug'], {}).get(locale) or e['description'].get(locale) or e['description']['en']
        rows.append(f"| [{title}](#{e['slug']}) | {html.escape(description).replace('|', '&#124;')} |")
    return '\n'.join(rows) + '\n'


def media_url(url):
    mapping = presentation().get('media', {})
    mapped = mapping.get(url, url)
    if not mapped.startswith('https://media.reeldance.ai/'):
        raise ValueError('README media requires a corresponding project CDN asset: ' + url)
    return mapped


def external_links(markdown):
    # Only authored links outside fenced prompts. Source text stays byte-for-byte.
    lines = []
    fence_length = None
    pattern = re.compile(r'(?<!!)\[([^\]\n]+)\]\((https?://[^\s)]+)\)')
    def anchor(match):
        return '<a href="' + html.escape(match[2], quote=True) + '" rel="nofollow noreferrer" referrerpolicy="no-referrer">' + html.escape(match[1]) + '</a>'
    for line in markdown.splitlines(keepends=True):
        fence = re.match(r'^(`{3,})([^`]*)$', line.rstrip('\r\n'))
        if fence and fence_length is None:
            fence_length = len(fence[1])
            lines.append(line)
        elif fence_length is not None:
            lines.append(line)
            if fence and len(fence[1]) >= fence_length and not fence[2].strip():
                fence_length = None
        else:
            lines.append(pattern.sub(anchor, line))
    return ''.join(lines)
