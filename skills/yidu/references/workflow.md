# Yidu runtime and workflow

Yidu uses the fixed upstream revision:

- repository: `https://github.com/yihong0618/bilingual_book_maker.git`
- commit: `e1027a4823e98f668ef950740b6f805ec30bd3b2`
- Pandoc: `3.1.12` for the private PDF runtime when no suitable system Pandoc exists

## Runtime preparation

Always prepare the runtime before reading the user's book. The wrapper is
idempotent and handles the dependency profile:

```bash
python "$YIDU_SKILL/scripts/run_runtime.py" \
  --book "$BOOK" \
  -- make_book.py --help
```

For an EPUB it installs the fixed base requirements. For a PDF it additionally
installs the fixed CPU-safe PDF requirements and prepares Pandoc 3.1.12. The
runtime lives under `$CODEX_HOME/runtimes/yidu/<commit>` (or the directory
selected by `BOOK_TRANSLATOR_RUNTIME`), never in system Python and never in the
book's work directory.

If the user needs a read-only diagnostic, use:

```bash
python "$YIDU_SKILL/scripts/ensure_runtime.py" \
  --book "$BOOK" --check --json
```

Do not run `pip install` manually, activate a shell environment, or add a
permanent PATH entry. The wrapper supplies the correct venv and Pandoc path.

## EPUB

Use the confirmed glossary rendered by `scripts/render_glossary.py`:

```bash
python "$YIDU_SKILL/scripts/run_runtime.py" \
  --book "$BOOK" \
  -- make_book.py \
  --book_name "$BOOK" \
  --api_format codex \
  --language "zh-hant:Traditional Chinese" \
  --single_translate \
  --glossary "$GLOSSARY_PINS" \
  --glossary-auto on \
  --plan-classify agent \
  --use_context session
```

The first invocation is the upstream plan/classification handoff. Review the
generated plan and resolve all `action: null` rows. Then run the small smoke
translation and inspect an early and late unit. For a full run, add `--quiet`
and redirect to a sibling `run.log`; add `--resume` only after a cache or smoke
run exists. Do not use `--parallel-workers` with the Codex route or session
context.

The upstream may use its own output suffix. Validate that file first with
`scripts/validate_epub.py`, then move it to `<stem>_zh-Hant.epub` or
`<stem>_bilingual_zh-Hant.epub` without overwriting an existing file.

## PDF

PDF translation is a reflowable EPUB conversion. The first command must use
the two-page preview:

```bash
python "$YIDU_SKILL/scripts/run_runtime.py" \
  --book "$BOOK" \
  -- make_book.py \
  --book_name "$BOOK" \
  --api_format codex \
  --language "zh-hant:Traditional Chinese" \
  --single_translate \
  --glossary "$GLOSSARY_PINS" \
  --to-epub \
  --pages 1-2 \
  --test
```

Read the generated `source.md` before approving the full run. For an English
scan after the user confirms the OCR warning, add `--pdf-ocr --ocr-lang iso:en`.
Only add `--ocr-replace-layer` when the embedded layer is visibly wrong. The
full PDF route reuses extraction and completed translation on rerun; it does
not use the EPUB `--resume` flow.

The runtime health check happens before the PDF parser opens the document and
before a paid translation request. If the dependency download fails, preserve
the partial runtime and report the exact retry command; do not delete it or
start the translation with a weaker fallback.

## Environment and credentials

The Codex route uses the user's existing Codex login. Do not put an API key on
the command line, in the runtime manifest, or in the repository. The runtime
manifest contains paths and versions only.
