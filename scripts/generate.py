"""Deterministic README, category index and complete catalog export."""
import argparse
import hashlib
import html
import json
import re
from pathlib import Path
from catalog import ROOT, load_entries, read_json, prompt_for
from readme import template, featured_entries, featured_navigation, media_url, external_links, presentation


def dump(value):
    return json.dumps(value, ensure_ascii=False, indent=2) + '\n'


def text(value):
    return re.sub(r'([\\`*_{}\[\]()#+!|])', r'\\\1', html.escape(value, quote=False))


def localized(values, locale):
    return values.get(locale) or values['en']


def fenced(prompt):
    longest = max([len(m.group()) for m in re.finditer(r'`+', prompt)] + [2])
    fence = '`' * (longest + 1)
    return fence + 'text\n' + prompt + '\n' + fence


def render_readme(entries, taxonomy, locale):
    zh = locale == 'zh'
    lines = [template('intro', locale, entries), '', featured_navigation(entries, locale), '', ('## 分类浏览' if zh else '## Browse categories'), '', ('同一作品可属于多个分类。' if zh else 'One artwork can appear in more than one category.'), '']
    for axis in ['use', 'style', 'subject']:
        lines += [('### ' + {'use':'用途','style':'风格','subject':'主体'}[axis]) if zh else '### ' + axis.title(), '', '| ' + ('分类 | 作品 | JSON |' if zh else 'Category | Artworks | JSON |'), '| --- | ---: | --- |']
        for key, label in taxonomy[axis].items():
            count = sum(key in e['categories'][axis] for e in entries)
            if count == 0:
                continue
            lines.append(f'| {text(localized(label, locale))} | {count} | [JSON](references/{axis}/{key}.json) |')
        lines.append('')
    lines += ['## ' + ('作品与提示词' if zh else 'Artwork & prompts'), '']
    for e in featured_entries(entries):
        prompt, language, fallback = prompt_for(e, locale)
        lines += [f'<a id="{e["slug"]}"></a>', '### ' + text(localized(e['title'], locale)), '', text(localized(e['description'], locale)), '',
                  ('作者：' if zh else 'By ') + text(e['author']['name']) + ((' (@' + text(e['author']['handle']) + ')') if e['author'].get('handle') else '') + ' · [' + ('原帖' if zh else 'Original post') + '](' + e['sourceUrl'] + ')', '',
                  ('类型：' if zh else 'Kind: ') + ({'text-to-image':'文生图', 'image-editing':'图像编辑'}[e['promptKind']] if zh else e['promptKind']) + ' · ' + text((presentation()['inputRequirementsZh'].get(e['slug'], '无需参考图片。')) if zh else e['inputRequirement']), '']
        if e.get('mediaSourceUrl') and e['mediaSourceUrl'] != e['sourceUrl']:
            lines += [('图片原帖：' if zh else 'Artwork source: ') + '[' + ('作者引用的输出作品' if zh else 'Author-quoted output artwork') + '](' + e['mediaSourceUrl'] + ')', '']
        output = next(m for m in e['media'] if m['role'] == 'output')
        lines += [f'![{text(output["alt"])}]({media_url(output["url"])})', '', ' · '.join(f'[{m["role"]} {i + 1}]({media_url(m["url"])})' for i,m in enumerate(e['media'])), '',
                  '<details>', '<summary>' + ('完整原始提示词' if zh else 'Complete original prompt') + ' (' + e['originalLanguage'] + ')</summary>', '', fenced(e['originalPrompt']), '', '</details>', '']
        if prompt != e['originalPrompt']:
            lines += ['<details>', '<summary>' + ('译文' if zh else 'Translation') + ' (' + language + ')</summary>', '', fenced(prompt), '', '</details>', '']
    lines += [template('footer', locale, entries), '']
    return external_links('\n'.join(lines))


def build_outputs(entries=None):
    entries = load_entries() if entries is None else entries
    entries = sorted(entries, key=lambda e: e['id'])
    taxonomy = read_json(ROOT / 'content/taxonomy.json')
    outputs = {}
    full = []
    for entry in entries:
        item = dict(entry)
        item['originalPromptSha256'] = hashlib.sha256(entry['originalPrompt'].encode()).hexdigest()
        item['localizedPrompts'] = {locale: dict(zip(['text','language','fallback'], prompt_for(entry, locale))) for locale in ['en','zh']}
        full.append(item)
    outputs['export/catalog.json'] = dump({'schemaVersion':1, 'model':'GPT Image 2.5', 'count':len(entries), 'entries':full})
    categories = []
    for axis, options in taxonomy.items():
        for key, labels in options.items():
            items = [e for e in entries if key in e['categories'][axis]]
            path = f'references/{axis}/{key}.json'
            outputs[path] = dump({'schemaVersion':1,'model':'GPT Image 2.5','axis':axis,'category':key,'labels':labels,'count':len(items),'entryIds':[e['id'] for e in items]})
            categories.append({'axis':axis,'category':key,'labels':labels,'count':len(items),'path':path})
    for locale, path in [('en','README.md'),('zh','README.zh-CN.md')]:
        outputs[path] = render_readme(entries, taxonomy, locale)
    hashes = {path:hashlib.sha256(value.encode()).hexdigest() for path,value in sorted(outputs.items())}
    outputs['references/manifest.json'] = dump({'schemaVersion':1,'model':'GPT Image 2.5','totalArtworks':len(entries),'catalog':'export/catalog.json','categories':categories,'sha256':hashes})
    return outputs


def generate(check=False):
    outputs = build_outputs()
    expected = set(outputs)
    actual = {str(p.relative_to(ROOT)) for folder in ['references','export'] for p in (ROOT/folder).rglob('*.json')}
    stale = actual - expected
    changed = [name for name,value in outputs.items() if not (ROOT/name).exists() or (ROOT/name).read_text(encoding='utf-8') != value]
    if check:
        if stale or changed:
            raise ValueError(f'Generated files are stale: {sorted(stale | set(changed))}; run python3 scripts/generate.py')
    else:
        for name in stale:
            (ROOT/name).unlink()
        for name,value in outputs.items():
            target = ROOT/name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(value, encoding='utf-8')
    print(f'{"Checked" if check else "Generated"} {len(outputs)} files')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    generate(parser.parse_args().check)
