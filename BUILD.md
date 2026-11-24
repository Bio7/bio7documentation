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

## The Bio7 API

The Java API (Javadoc) in the folder `api/` is generated from the sources of Bio7; the documented classes are listed in `api_classes.txt`:

```bash
./make_api.sh <bio7 repository> <Eclipse folder of an installed Bio7>
# e.g. ./make_api.sh ~/git/bio7 /Applications/Bio7.app/Contents/Eclipse
```

The plugins of the installed Bio7 are the classpath and its JDK runs javadoc (English texts, no time stamps). If the installed Bio7 is older than the repository (a documented class uses a new class of another package), list that source in `api_support.txt` (used for the symbols, not documented); a failed run keeps the existing `api/`. GitHub Pages publishes it at <https://bio7.github.io/bio7documentation/api/index.html>.

Note: eLyXer needs Python 3.10 or older (newer versions removed the file mode it uses).

## License

© 2005-2026 M. Austenfeld
