# Runtime and workflow

The skill uses the pinned upstream revision:

- repository: `https://github.com/yihong0618/bilingual_book_maker.git`
- commit: `e1027a4823e98f668ef950740b6f805ec30bd3b2`
- prepare with: `python /path/to/skill/scripts/ensure_upstream.py --print-root`

The first setup may need the upstream Python dependencies. Keep them in the
upstream runtime environment; do not install packages into the user's system
Python without explaining the change. The Codex route uses the user's existing
Codex login and does not put an API key on the command line.

## EPUB

Use a confirmed glossary rendered by `scripts/render_glossary.py`:

```bash
python "$RUNTIME/make_book.py" \
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

PDF translation is a reflowable EPUB conversion. Check the PDF extra and
Pandoc before opening the file. Always do a two-page extraction/preview first:

```bash
python "$RUNTIME/make_book.py" \
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

For both formats, keep the work directory until the user accepts the output.
Run the structural validator and glossary consistency report before delivery.
