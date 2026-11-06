#!/bin/bash
# Builds the versions of the Bio7 manual:
#   Main.html        the classic eLyXer version (bio7.css)
#   Bio7_Manual.html a modern version (sidebar, search, light and dark theme)
#   Bio7_Manual.pdf  a PDF of the modern version (Google Chrome, the Python
#                    packages pypdf and pymupdf for the page numbers of the
#                    contents and a smaller file)
#   markdown/        only with the argument "markdown": a Markdown version
#                    (pandoc and beautifulsoup4)
cd "$(dirname "$0")" || exit 1
python3 /usr/local/bin/elyxer --mathjax remote --css bio7.css Main.lyx Main.html || exit 1
python3 modernize.py Main.html Bio7_Manual.html || exit 1
python3 make_pdf.py Bio7_Manual.html Bio7_Manual.pdf
if [ "$1" = "markdown" ]; then
  rm -rf markdown
  python3 make_markdown.py Bio7_Manual.html markdown
fi
