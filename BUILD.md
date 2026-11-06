# Building the Bio7 Manual

The manual is written in [LyX](https://www.lyx.org) (`Main.lyx` includes the chapters). The script `build.sh` builds the HTML and Markdown versions, the PDF is built on demand:

```bash
./build.sh          # Main.html, Bio7_Manual.html and README.md
./build.sh pdf      # in addition Bio7_Manual.pdf
```

| Step | Tool | Output |
|------|------|--------|
| `elyxer --css bio7.css Main.lyx Main.html` | [eLyXer](https://github.com/alexfernandez/elyxer) | `Main.html` |
| `modernize.py` | Python 3 | `Bio7_Manual.html` |
| `make_pdf.py` | Google Chrome, Python package `pypdf` | `Bio7_Manual.pdf` (built on demand, not in the repository) |
| `make_markdown.py` | [pandoc](https://pandoc.org), Python package `beautifulsoup4` | `README.md` (the whole manual) |

The images are in the folder `images` (the screenshots of Bio7 4.0 were made with the dark theme).

## License

© 2005-2026 M. Austenfeld
