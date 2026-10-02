# Data contract

`content/entries/*.json` and `content/taxonomy.json` are the only authored catalog sources. README and exports are deterministic derivatives; edit the source files to change them.

| Path | Purpose |
| --- | --- |
| `content/entries/<id>.json` | One original artwork, full prompt, author, model claim, media and rights |
| `content/taxonomy.json` | Allowed category slugs and English/Chinese labels |
| `schema/entry.schema.json` | JSON Schema 2020-12; additional fields rejected |
| `README.md`, `README.zh-CN.md` | Browseable catalog with thumbnails, all media links and complete prompts |
| `export/catalog.json` | Complete original fields plus resolved `localizedPrompts` |
| `references/<axis>/<category>.json` | Category's unique artwork IDs and count |
| `references/manifest.json` | Category files, counts, catalog path and SHA-256 output hashes |
| `scripts/prepare_submission.py` | Approved issue to pending JSON artifact |

## Consumer example

A page can fetch the raw catalog without a CMS or API key:

```js
const base = 'https://raw.githubusercontent.com/BravoNeo/awesome-gpt-image-2-5-prompts/main/';
const catalog = await fetch(base + 'export/catalog.json').then(r => r.json());
const manifest = await fetch(base + 'references/manifest.json').then(r => r.json());
const posters = await fetch(base + 'references/use/posters.json').then(r => r.json());
const byId = new Map(catalog.entries.map(entry => [entry.id, entry]));
const items = posters.entryIds.map(id => byId.get(id));
```

Use a commit SHA in place of `main` for a consistent snapshot across requests. `schemaVersion` is currently `1`; changing the contract requires an intentional version bump. No website deployment is included in this repository.

## IDs, count and translations

X/Twitter status URLs normalize by status ID, ignoring handles, tracking query strings and fragments. The ID is `x-<status-id>`. Other HTTPS sources use `web-` plus the first 16 hex characters of SHA-256 of their canonical URL (hostname lowercased, trailing slash and fragment removed; meaningful query retained). Rename the file only when correcting the original source itself.

A source URL, ID or slug may appear only once. Media form an array with `input` or `output` roles. A four-image post is one artwork. Each category counts distinct entries; category totals across different categories are not additive.

`modelClaimed` records the credited author's model designation and is fixed to `GPT Image 2.5` for this collection. GPT Image 2 and 1.5 entries are outside its scope. `originalPrompt` is preserved exactly. Translations are separate optional text. `localizedPrompts.<locale>` reports `text`, its actual `language`, and whether `fallback` was used. Missing title/description translations fall back to English.

## Operations

All scripts use the Python standard library. `catalog.py` implements the JSON Schema keywords present in the checked-in schema and fails on unsupported keywords; it also enforces canonical IDs and taxonomy membership. It never fetches media. `generate.py --check` checks reproducibility and obsolete generated JSON files. The manifest hashes every generated file except itself.

CI runs on ordinary pull requests and main pushes with read-only permissions. The content generator only runs automatically for `content/**` pushes to main and can be dispatched manually. Its single write permission is repository contents, to commit generated files. Protected branches that block bot pushes require committing generated outputs in the content PR (the normal contributor flow already does this); remove bot direct writes if your branch rules demand it.

Approved submissions use a read-only issue workflow, validate the labeling actor's repository permission through the GitHub API, fetch the current issue, and upload pending JSON. Issue text is parsed as data; no issue expression is embedded in shell commands, no URLs are downloaded, and no PR is automatically merged. No `pull_request_target` workflow exists. GitHub Actions must be enabled; the `submission` and `approved` labels should exist. No additional tokens or secrets are needed.
