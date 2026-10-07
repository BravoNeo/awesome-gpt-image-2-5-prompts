import copy
import hashlib
import json
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from catalog import ROOT, load_entries, validate_entries, stable_id, canonical_source, prompt_for, validate_schema, read_json
from generate import build_outputs, render_readme
from prepare_submission import FIELDS, parse_issue
import prepare_submission
from unittest import mock


class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.entries = load_entries()
        self.entry = copy.deepcopy(self.entries[0])

    def test_seed_originals_and_model(self):
        self.assertGreater(len(self.entries), 0)
        self.assertEqual({e['modelClaimed'] for e in self.entries}, {'GPT Image 2.5'})

    def test_same_post_many_images_count_once(self):
        travel = copy.deepcopy(self.entry)
        travel['categories']['use'] = ['posters']
        travel['media'] = [dict(travel['media'][0], url=f'https://example.com/output-{i}.jpg') for i in range(4)]
        validate_entries([travel])
        # Synthetic count fixture has no uploaded CDN assets; it is never exported.
        with mock.patch('generate.media_url', side_effect=lambda url: 'https://media.reeldance.ai/test-fixtures/' + url.rsplit('/', 1)[-1]):
            outputs = build_outputs([travel])
        self.assertEqual(json.loads(outputs['references/use/posters.json'])['count'],1)
        self.assertEqual(json.loads(outputs['export/catalog.json'])['count'],1)

    def test_duplicate_id_rejected(self):
        with self.assertRaisesRegex(ValueError,'Duplicate id'):
            validate_entries([self.entry, copy.deepcopy(self.entry)])

    def test_alias_source_dedup(self):
        e = self.entry
        status = e['sourceUrl'].rsplit('/',1)[1]
        alias = f'https://twitter.com/other/status/{status}?s=20#photo'
        self.assertEqual(stable_id(alias),e['id'])
        self.assertEqual(canonical_source(alias),canonical_source(e['sourceUrl']))
        dupe=copy.deepcopy(e)
        dupe['sourceUrl']=alias
        dupe['slug']='another-slug'
        with self.assertRaisesRegex(ValueError,'Duplicate id'):
            validate_entries([e,dupe])

    def test_id_not_title_derived(self):
        self.entry['title']['en']='Changed title'
        self.entry['slug']='changed-title'
        validate_entries([self.entry])
        self.assertEqual(self.entry['id'],stable_id(self.entry['sourceUrl']))
        self.entry['id']='x-999999'
        with self.assertRaisesRegex(ValueError,'ID must'):
            validate_entries([self.entry])

    def test_duplicate_slug_rejected(self):
        self.entries[1]['slug']=self.entries[0]['slug']
        with self.assertRaisesRegex(ValueError,'Duplicate slug'):
            validate_entries(self.entries)

    def test_unknown_category_rejected(self):
        self.entry['categories']['use']=['unknown-category']
        with self.assertRaisesRegex(ValueError,'Unknown category'):
            validate_entries([self.entry])

    def test_non_25_model_rejected(self):
        for model in ['GPT Image 2','GPT Image 1.5','gpt-image-2.5']:
            self.entry['modelClaimed']=model
            with self.assertRaises(ValueError):
                validate_entries([self.entry])

    def test_schema_unknown_and_missing_fields(self):
        self.entry['internalRecord']='do not publish'
        with self.assertRaisesRegex(ValueError,'unknown'):
            validate_entries([self.entry])
        self.entry.pop('internalRecord')
        self.entry.pop('author')
        with self.assertRaisesRegex(ValueError,'missing'):
            validate_entries([self.entry])

    def test_media_roles_and_duplicate_urls(self):
        self.entry['media'][0]['role']='bad-role'
        with self.assertRaises(ValueError):
            validate_entries([self.entry])
        self.entry['media'][0]['role']='output'
        self.entry['media'].append(copy.deepcopy(self.entry['media'][0]))
        with self.assertRaisesRegex(ValueError,'Duplicate media'):
            validate_entries([self.entry])
        for m in self.entry['media']:
            m['role']='input'
        with self.assertRaisesRegex(ValueError,'output image'):
            validate_entries([self.entry])

    def test_output_source_credit(self):
        self.entry['media'][0]['sourceUrl']='https://x.com/another/status/12345'
        with self.assertRaisesRegex(ValueError,'credit'):
            validate_entries([self.entry])

    def test_unsafe_url_rejected(self):
        for url in ['http://example.com/post','https://user:password@example.com/post','https://localhost/post','https://example.com/"bad']:
            with self.assertRaises(ValueError):
                stable_id(url)

    def test_translation_fallback_and_preservation(self):
        self.entry['originalLanguage']='en'
        self.entry['translations']={}
        original=self.entry['originalPrompt']
        self.assertEqual(prompt_for(self.entry,'zh'),(original,'en',True))
        self.entry['translations']['zh']='中文译文'
        self.entry['translations']['en']='Must not replace the original'
        self.assertEqual(prompt_for(self.entry,'zh'),('中文译文','zh',False))
        self.assertEqual(prompt_for(self.entry,'en'),(original,'en',False))
        full=json.loads(build_outputs([self.entry])['export/catalog.json'])['entries'][0]
        self.assertEqual(full['originalPrompt'],original)
        self.assertEqual(full['originalPromptSha256'],hashlib.sha256(original.encode()).hexdigest())
        self.assertEqual(full['localizedPrompts']['zh']['text'],'中文译文')

    def test_japanese_original_fallback(self):
        self.entry['originalLanguage']='ja'
        self.entry['originalPrompt']='参照画像の人物を主題にしてください。'
        self.entry['translations']={}
        validate_entries([self.entry])
        self.assertEqual(prompt_for(self.entry,'en'),(self.entry['originalPrompt'],'ja',True))
        self.assertEqual(prompt_for(self.entry,'zh'),(self.entry['originalPrompt'],'ja',True))
        self.entry['translations']['en']='Use the person in the reference image.'
        self.assertEqual(prompt_for(self.entry,'en'),(self.entry['translations']['en'],'en',False))

    def test_explicit_quoted_output_binding(self):
        e=self.entry
        e['promptSourceUrl']=e['sourceUrl']
        e['mediaSourceUrl']='https://x.com/author/status/123456789'
        e['mediaBinding']='author-quoted-output'
        for m in e['media']:
            m['sourceUrl']=e['mediaSourceUrl']
            m['role']='output'
        validate_entries([e])
        outputs=build_outputs([e])
        self.assertIn(e['mediaSourceUrl'],outputs['README.md'])
        full=json.loads(outputs['export/catalog.json'])['entries'][0]
        self.assertEqual(full['promptSourceUrl'],e['sourceUrl'])
        self.assertEqual(full['mediaSourceUrl'],e['mediaSourceUrl'])
        self.assertEqual({m['role'] for m in full['media']},{'output'})
        e['mediaBinding']='direct-source'
        with self.assertRaisesRegex(ValueError,'Separate output source'):
            validate_entries([e])

    def test_source_binding_fields_and_prompt_source(self):
        self.entry['promptSourceUrl']=self.entry['sourceUrl']
        self.entry.pop('mediaSourceUrl',None)
        self.entry.pop('mediaBinding',None)
        with self.assertRaisesRegex(ValueError,'together'):
            validate_entries([self.entry])
        self.entry['mediaSourceUrl']=self.entry['sourceUrl']
        self.entry['mediaBinding']='direct-source'
        self.entry['promptSourceUrl']='https://x.com/other/status/123456789'
        with self.assertRaisesRegex(ValueError,'Prompt source'):
            validate_entries([self.entry])

    def test_counts_links_hashes_and_determinism(self):
        outputs=build_outputs()
        self.assertEqual(outputs,build_outputs(list(reversed(self.entries))))
        manifest=json.loads(outputs['references/manifest.json'])
        self.assertEqual(manifest['totalArtworks'],len(self.entries))
        ids={e['id'] for e in self.entries}
        for category in manifest['categories']:
            if category['count'] == 0:
                self.assertNotIn(f"]({category['path']})", outputs['README.md'])
                self.assertNotIn(f"]({category['path']})", outputs['README.zh-CN.md'])
                continue
            index=json.loads(outputs[category['path']])
            self.assertEqual(index['count'],len(set(index['entryIds'])))
            self.assertLessEqual(set(index['entryIds']),ids)
            self.assertIn(f"]({category['path']})",outputs['README.md'])
            self.assertIn(f"]({category['path']})",outputs['README.zh-CN.md'])
        for path,digest in manifest['sha256'].items():
            self.assertEqual(hashlib.sha256(outputs[path].encode()).hexdigest(),digest)
        for readme in ['README.md','README.zh-CN.md']:
            for link in re.findall(r'\]\(([^\s)]+)\)',outputs[readme]):
                if link.startswith('#'):
                    self.assertIn('id="' + link[1:] + '"', outputs[readme])
                elif not link.startswith('https://'):
                    self.assertTrue(link in outputs or (ROOT/link).is_file(),link)
            for e in self.entries:
                self.assertIn(e['sourceUrl'],outputs[readme])
                self.assertIn(e['originalPrompt'], outputs[readme])
                self.assertIn(e['originalPrompt'], [i['originalPrompt'] for i in json.loads(outputs['export/catalog.json'])['entries']])

    def test_markdown_input_stays_inert(self):
        self.entry['title']['en']='<script>alert(1)</script> [click](javascript:x)'
        self.entry['originalPrompt']='```\n</details>\n$(touch /tmp/never-execute)\n### Custom heading\n'
        readme=build_outputs([self.entry])['README.md']
        self.assertNotIn('<script>',readme)
        self.assertIn('````text',readme)
        self.assertIn('$(touch /tmp/never-execute)',readme)

    def test_duplicate_json_keys_fail(self):
        import tempfile
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'entry.json'
            p.write_text('{"id":"one","id":"two"}')
            with self.assertRaisesRegex(ValueError,'Duplicate JSON key'):
                read_json(p)

    def test_schema_unsupported_keywords_fail(self):
        with self.assertRaisesRegex(ValueError,'Unsupported schema keyword'):
            validate_schema('x',{'type':'string','unknownKeyword':True})


class SubmissionTests(unittest.TestCase):
    def body(self):
        e=load_entries()[0]
        values={
            'Title (English)':e['title']['en'], 'Title (Chinese, optional)':'_No response_',
            'Description (English)':e['description']['en'],'Description (Chinese, optional)':'_No response_',
            'Original prompt':e['originalPrompt']+'\n\n### Custom heading\n$(touch /tmp/not-executed)',
            'Original language':'en','Translations JSON (optional)':'_No response_',
            'Author name':e['author']['name'],'Author handle (optional)':e['author']['handle'],
            'Original post URL':e['sourceUrl'],'Model':'GPT Image 2.5','Prompt kind':'text-to-image',
            'Reference input requirement':'No reference image required.','Media JSON':json.dumps(e['media']),
            'Categories JSON':json.dumps(e['categories']),'Tags JSON (optional)':'_No response_',
            'Contribution permission':'- [x] I have permission to contribute this prompt and these media links.'}
        return '\n\n'.join('### '+f+'\n\n'+values[f] for f in FIELDS)

    def test_form_to_pending_json_only(self):
        e=parse_issue(self.body())
        validate_entries([e])
        self.assertIn('### Custom heading',e['originalPrompt'])
        self.assertIn('$(touch /tmp/not-executed)',e['originalPrompt'])
        self.assertEqual(e['translations'],{})
        self.assertEqual(e['rights']['basis'],'submitter-permission')
        self.assertNotIn('zh',e['title'])

    def test_missing_permission_or_duplicate_heading(self):
        with self.assertRaisesRegex(ValueError,'permission'):
            parse_issue(self.body().replace('- [x]','- [ ]'))
        with self.assertRaisesRegex(ValueError,'Duplicate form heading'):
            parse_issue(self.body()+'\n\n### Model\n\nGPT Image 2.5')

    def test_malformed_json_rejected(self):
        with self.assertRaises((ValueError,json.JSONDecodeError)):
            parse_issue(self.body().replace('### Media JSON','### Media JSON invalid'))


    def run_event(self, permission='admin', state='open', labels=None):
        import tempfile
        import os
        body=self.body()
        event={'action':'labeled','label':{'name':'approved'},'sender':{'login':'BravoNeo'},'issue':{'number':123}}
        issue={'state':state,'labels':labels if labels is not None else [{'name':'approved'}],'body':body}
        with tempfile.TemporaryDirectory() as folder:
            event_path=Path(folder)/'event.json'
            event_path.write_text(json.dumps(event))
            cwd=os.getcwd()
            try:
                os.chdir(folder)
                with mock.patch.dict(os.environ,{'GITHUB_EVENT_PATH':str(event_path),'GITHUB_REPOSITORY':'BravoNeo/example'}), mock.patch.object(prepare_submission,'api',side_effect=[{'permission':permission},issue]), mock.patch.object(prepare_submission,'load_entries',return_value=[]):
                    prepare_submission.main()
                files=list((Path(folder)/'pending').glob('*.json'))
                self.assertEqual(len(files),1)
                validate_entries([read_json(files[0])])
            finally:
                os.chdir(cwd)

    def test_approved_pipeline_artifact(self):
        self.run_event()

    def test_unprivileged_actor_rejected(self):
        with self.assertRaisesRegex(ValueError,'Only maintainers'):
            self.run_event(permission='read')

    def test_removed_label_and_closed_issue_rejected(self):
        with self.assertRaisesRegex(ValueError,'open approved'):
            self.run_event(labels=[])
        with self.assertRaisesRegex(ValueError,'open approved'):
            self.run_event(state='closed')


if __name__=='__main__':
    unittest.main()
