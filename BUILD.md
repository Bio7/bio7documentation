# Building the Bio7 Manual

The manual is written in [LyX](https://www.lyx.org) (`Main.lyx` includes the chapters, the images are in the folder `images`, the screenshots of Bio7 4.0 were made with the dark theme). The script `build.sh` builds the HTML and PDF versions:

```bash
./build.sh            # Main.html, Bio7_Manual.html and Bio7_Manual.pdf
./build.sh markdown   # in addition a Markdown version in the folder markdown
```

| Step | Tool | Output |
|------|------|--------|
| `elyxer --css bio7.css Main.lyx Main.html` | [eLyXer](https://github.com/alexfernandez/elyxer) | `Main.html` |
| `modernize.py` | Python 3 | `Bio7_Manual.html` |
| `make_pdf.py` | Google Chrome, Python packages `pypdf` (page numbers of the contents) and `pymupdf` (a smaller file) | `Bio7_Manual.pdf` |
| `make_markdown.py` | [pandoc](https://pandoc.org), Python package `beautifulsoup4` | `markdown/` (one file per chapter, not in the repository) |

## License

© 2005-2026 M. Austenfeld
