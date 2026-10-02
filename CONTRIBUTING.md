# Contributing / 投稿

Contribute GPT Image 2.5 prompts through the [submission form](https://github.com/BravoNeo/awesome-gpt-image-2-5-prompts/issues/new?template=submit-prompt.yml) or a pull request. Include the complete original prompt, original author and post URL, model name, image links, and permission to contribute them. Keep all images from the same artwork together.

欢迎通过 Issue 表单或 PR 投稿 GPT Image 2.5 作品。请保留完整原文、作者、原帖、多图角色和贡献权限。同一原帖的多张图片只算一个作品。

## Submit an issue

1. Fill in the form. `Media JSON` is an array of HTTPS links, each with `url`, `role` (`input` or `output`), `alt` and `sourceUrl`. At least one output is required. For output images, use the artwork's original post as `sourceUrl`. If the author explicitly quotes their output from another post, contribute through a PR with `promptSourceUrl`, `mediaSourceUrl` and `mediaBinding: "author-quoted-output"` as described in the data contract.
2. Choose category slugs from [content/taxonomy.json](content/taxonomy.json) for `use`, `style` and `subject`. Ask for a new category in the issue if needed.
3. A maintainer with write, maintain or admin permission applies `approved`. The workflow reads the current issue, checks that the actor is a maintainer, and prepares a `pending-submission` JSON artifact in [Actions](https://github.com/BravoNeo/awesome-gpt-image-2-5-prompts/actions/workflows/approved-submission.yml).
4. The maintainer downloads and reviews the artifact, copies the JSON into `content/entries/`, generates outputs, and opens a pull request. Applying a label never writes contributor text to `main`.

The artifact reflects the current issue body at the time of the run. It remains pending until the maintainer reviews and merges that exact JSON. If the issue changes, remove and reapply `approved` to prepare a fresh artifact. Failed validation appears in the workflow run; correct the issue fields and reapply the label.

## Submit a pull request

Use Python 3.9 or newer. No package install, paid API, CMS, or LLM key is required.

```bash
python3 scripts/catalog.py
python3 -m unittest discover -s tests -v
python3 scripts/generate.py
python3 scripts/generate.py --check
```

Add one JSON file per original artwork, named `<id>.json`, matching [the schema](schema/entry.schema.json). Derive IDs with:

```bash
python3 -c 'import sys; sys.path.insert(0,"scripts"); from catalog import stable_id; print(stable_id("https://x.com/author/status/123456789"))'
```

Keep `id` stable if you change a title, slug or translation. Add translations under `translations.en` or `translations.zh`, preserving the original in `originalPrompt`. Original prompts may be English, Chinese or Japanese. Titles and descriptions always need English; Chinese is optional. Missing translations fall back to the original prompt. For an edit, describe the reference image requirement; attach an input link only if it is available and you have permission to share it.

Commit the source JSON and generated files together. CI validates the schema, unique IDs and original sources, taxonomy, image roles and generated output. After content changes merge, the generator refreshes README and JSON files automatically. For changes to scripts or schema, regenerate locally or manually run **Generate catalog**.

## Rights

Contribute only material you have permission to share and credit its author. Do not use the code's MIT license to relicense third-party images or prompts. Link to publicly hosted media; do not upload another author's files without their permission. See [CONTENT_RIGHTS.md](CONTENT_RIGHTS.md).
