#!/bin/bash
# Builds the versions of the Bio7 manual:
#   Main.html        the classic eLyXer version (bio7.css)
#   Bio7_Manual.html a modern version (sidebar, search, light and dark theme)
#   README.md        the Markdown version (the whole manual, the start page on
#                    GitHub, pandoc and beautifulsoup4)
#   Bio7_Manual.pdf  only with the argument "pdf" (Google Chrome, page numbers of
#                    the contents with the Python package pypdf: pip install pypdf)
cd "$(dirname "$0")" || exit 1
python3 /usr/local/bin/elyxer --mathjax remote --css bio7.css Main.lyx Main.html || exit 1
python3 modernize.py Main.html Bio7_Manual.html || exit 1
if command -v pandoc > /dev/null; then
  python3 make_markdown.py Bio7_Manual.html . --single
else
  echo "pandoc is not available: no Markdown version (https://pandoc.org)"
fi
if [ "$1" = "pdf" ]; then
  python3 make_pdf.py Bio7_Manual.html Bio7_Manual.pdf
fi
