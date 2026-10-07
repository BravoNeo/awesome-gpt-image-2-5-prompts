# Maintaining the GPT Image 2.5 collection

See [the data contract](data-contract.md), [CONTRIBUTING](../CONTRIBUTING.md) and the source validation scripts for the data workflow.

## Portfolio documentation

English and Chinese READMEs are generated from the existing catalog plus the
presentation-only `docs/readme-intro.*.md`, `docs/readme-footer.*.md` and
`docs/readme-presentation.json`. Featured ordering and descriptions affect the
README only. Full original prompts remain separate from translations or editorial
adaptations. Never edit prompt bytes, creator/source bindings, model statements,
media provenance or work counts as part of a documentation refresh.

README images, posters, linked videos and input-reference previews use corresponding
ReelDance CDN assets. The original media URLs remain in the source catalog.
The presentation media map must be updated from a reviewed matching CDN asset
when a new work is added; do not substitute another work's media. Preview sizes
are not claimed to be full-resolution source exports.

Authored external anchors carry `rel="nofollow noreferrer"` and
`referrerpolicy="no-referrer"`. No links request a new tab. GitHub sanitizes rendered
README HTML and controls its final attributes; these authored attributes are not
a guarantee of GitHub's referrer behavior or SEO treatment. Confirm the rendered
links on GitHub when publishing. A GitHub GFM API check on 2026-10-07 retained `rel="nofollow"` and removed `noreferrer` and `referrerpolicy`; custom anchor IDs received the `user-content-` prefix. See [GitHub's markup pipeline](https://github.com/github/markup#github-markup).
Prompt code blocks are excluded from link conversion and remain literal source text.

The README structure draws on the browsing and attribution conventions of
[YouMind's image collections](https://github.com/YouMind-OpenLab/awesome-nano-banana-pro-prompts).
ReelDance maintains this collection independently; editorial copy is original.

Run `python3 scripts/generate.py`, then the same command with `--check`, after changing presentation sources.

`references/manifest.json` includes README checksums. A docs-only refresh changes those two checksums; catalog and category JSON checksums must stay unchanged.

## Website synchronization

A documentation commit does not deploy ReelDance. Keep catalog and schema hashes
unchanged for a documentation-only release. The GPT gallery resolves main and
imports its catalog at a pinned commit for each build; Kling and Nano use reviewed
source locks. Any future data change requires the website's separate import,
validation and publication workflow. Do not update website source locks just to
point them at a README-only commit.
