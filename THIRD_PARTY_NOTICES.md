# Third-party notices

Yidu is distributed under the MIT License.

## bilingual_book_maker

Yidu prepares and runs the following fixed upstream revision at first use:

- Repository: <https://github.com/yihong0618/bilingual_book_maker>
- Commit: `e1027a4823e98f668ef950740b6f805ec30bd3b2`
- License: MIT; copyright belongs to the upstream authors.

## Pandoc

The PDF runtime uses Pandoc 3.1.12 when a suitable system Pandoc is not
available. Yidu downloads the platform archive from the official release and
keeps it in the user's private runtime directory. Pandoc is distributed under
its own license; see the upstream release and source repository:

- Release: <https://github.com/jgm/pandoc/releases/tag/3.1.12>
- Repository: <https://github.com/jgm/pandoc>

## Python dependencies

Docling, PyTorch, OCR runtimes, pypdfium2, and the other Python packages are
installed from the pinned requirement files shipped by the upstream commit.
Their respective licenses remain with their authors and distributions.
