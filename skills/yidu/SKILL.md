---
name: yidu
description: Translate English EPUB or PDF books into Taiwan Traditional Chinese EPUB with pinned terminology, interactive glossary confirmation, pure or bilingual output, OCR warnings, resumable runs, and structural validation. Use for book or e-book translation requests; do not use for DRM removal or public publishing.
---

# 譯讀 Yidu：英文書 → 台灣繁中

Translate a rights-cleared English book into a readable Taiwan Traditional Chinese EPUB by operating the pinned `bilingual_book_maker` runtime. The original file is never edited. This skill is for personal reading, research, and small internal sharing; it is not a publishing or DRM-removal workflow.

## User-facing interface

Accept natural-language requests such as:

- `翻譯 /path/to/book.epub 成台灣繁中`
- `把 /path/to/book.pdf 翻成台灣繁中 EPUB`
- `翻譯這本 EPUB，雙語模式`

Recognize `.epub` and `.pdf` only. The default output is translated-only Taiwan Traditional Chinese. Enable bilingual output only when the user explicitly asks for it.

Default translation settings:

- source: English; target: `zh-hant:Traditional Chinese`
- locale: Taiwan vocabulary, full-width punctuation, natural but faithful prose
- provider: Codex route (`--api_format codex`), using the user's Codex subscription
- EPUB: `--plan-classify agent`, `--use_context session`, `--single_translate`
- terminology: per-book glossary, confirmed before the full run, passed with `--glossary`
- AI disclosure: keep the upstream disclosure/credit line

## Safety and preflight

1. Confirm the input exists and is `.epub` or `.pdf`; stop with a concise error otherwise.
2. Confirm the user has the right to translate it. Never remove DRM or bypass encryption. For EPUB, stop when `META-INF/encryption.xml` indicates protected content.
3. Preserve the original file. Work only in a sibling `<stem>_translation_work/` directory and write output beside the source.
4. Warn that cloud model processing is used through Codex and that the result is not publication-grade without human editing.
5. Before opening the book, run the bundled runtime bootstrap through `scripts/run_runtime.py`. It prepares the fixed upstream commit, the per-user virtual environment, and the PDF-only dependencies when needed. Never silently use a moving branch.

The bootstrap is idempotent and writes only below `$CODEX_HOME/runtimes/yidu/<commit>` (or `BOOK_TRANSLATOR_RUNTIME`). It never uses `sudo`, changes system Python, or edits global PATH. A PDF first run can download a large Docling/PyTorch runtime and a private Pandoc 3.1.12 binary; tell the user before the download starts.

For upstream commands, use this shape and do not assemble a venv or PATH manually:

In the examples, `$YIDU_SKILL` means the directory containing this `SKILL.md`.
If that environment variable is not set, substitute the installed skill's
actual path.

```bash
python "$YIDU_SKILL/scripts/run_runtime.py" \
  --book "$BOOK" \
  -- make_book.py \
  --book_name "$BOOK" \
  ...upstream arguments...
```

The wrapper selects the EPUB or PDF profile from the input, runs the upstream command with its venv Python, and exposes the private Pandoc binary only to that process.

Read [references/workflow.md](references/workflow.md) for the exact EPUB/PDF command sequences and checkpoints. Read [references/glossary-format.md](references/glossary-format.md) when creating or validating a book glossary. Read [references/translation-prompt.md](references/translation-prompt.md) when constructing the Taiwan-style prompt.

## Terminology gate

Before paying for the full translation, inspect the book and create a ranked candidate glossary of recurring technical terms, named entities, and phrases that can drift. Show the user each candidate with:

- English term and a short source-language example
- proposed Taiwan Traditional Chinese rendering
- sense/context note
- any detected variants or competing translations

Ask the user to confirm, edit, or mark separate senses. Do not start the full run while a high-frequency or ambiguous candidate is unresolved. Save the authoritative glossary in the work directory and render the pinned `term -> translation` file expected by upstream. A confirmed entry is a hard constraint: for example, once `social self-efficacy → 社會自我效能` is accepted, do not emit `社交自我效能` for the same sense.

When the interactive question UI is available, ask one glossary decision at a time instead of presenting an unbounded questionnaire.

After translation, run `scripts/check_glossary_consistency.py` against the output. Report every likely variant. Repair only after checking the source context; do not blindly replace a genuine different sense.

## EPUB workflow

Follow the upstream `bbm-plan` flow:

1. Run `run_runtime.py` with the EPUB input and wait for the base runtime health check to pass.
2. Run the offline plan/classification pass. Review every unresolved structural signature; translate prose, headings, dialogue, captions, and poetry, while skipping code, URLs, page furniture, and decorative markers when justified by samples.
3. Run a small smoke translation after the glossary is confirmed. Read an early and late sample before authorizing the full run.
4. Run the full translation quietly in the background with the same settings and resume support. Use `--resume` only after a cache exists or after a smoke run.
5. Validate the output EPUB, including chapter order, TOC, metadata, inline attributes, code/URL preservation, no delimiter/JSON residue, and no unchanged translated prose.

Use these output names unless the user specifies another path:

- pure: `<source_stem>_zh-Hant.epub`
- bilingual: `<source_stem>_bilingual_zh-Hant.epub`

## PDF workflow

PDF input always uses the upstream `--to-epub` route and produces a reflowable EPUB, not a page-faithful PDF. Do not promise preservation of the original page layout.

1. Run `run_runtime.py` with the PDF input. It completes the full PDF dependency health check, including Docling, OCR modules, PyTorch, and Pandoc, before the PDF is opened or any model request is made.
2. Extract and translate the first two pages as a preview; inspect `source.md` headings and extraction quality before the full run.
3. For a text PDF, continue with the normal Codex/session route and confirmed glossary.
4. For a scan, stop at the OCR warning and ask for confirmation. Use `--pdf-ocr --ocr-lang iso:en` for an English scan. Use `--ocr-replace-layer` only when the embedded text layer is demonstrably wrong, not merely invisible.
5. Read back one early and one late section. Report that figures remain images, formula images are not translated/searchable, and complex layout may need manual repair.

## Delivery and stopping rules

- Keep the work directory and glossary until the user confirms the output is usable; offer cleanup only afterward.
- If a run fails, preserve the checkpoint/log and report the exact next safe resume action. Never delete the cache or retranslate silently.
- Stop before any paid full run when credentials, rights confirmation, glossary ambiguities, OCR quality, or the preview requires user input.
- Do not add TXT, Markdown, SRT, or public-publishing workflows to this skill.
