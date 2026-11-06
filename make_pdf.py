#!/usr/bin/env python3
"""
Creates a PDF of the Bio7 manual from the modern HTML version (see modernize.py)
with Google Chrome (headless): a cover page, a table of contents with page
numbers, chapters on new pages, page numbers and the bookmarks of the headings.

Usage (in the folder of the manual, after build.sh):
    python3 make_pdf.py Bio7_Manual.html Bio7_Manual.pdf

The page numbers of the table of contents are read from the bookmarks of a
first print (needs the Python package pypdf, else the table of contents has no
page numbers, the entries are links in both cases).
"""

import html
import os
import re
import subprocess
import sys
import tempfile

CHROME = os.environ.get("CHROME", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")


def strip_tags(s):
    return html.unescape(re.sub(r"<[^>]+>", "", s)).strip()


def build(src):
    s = open(src, encoding="utf-8").read()
    body = s[s.index('<main><div class="content">') + len('<main><div class="content">'):s.index("</div></main>")]
    title = strip_tags(re.search(r'<h1 class="title">(.*?)</h1>', body, re.S).group(1))
    authors = [strip_tags(a) for a in re.findall(r'<h2 class="author">(.*?)</h2>', body, re.S)]
    body = re.sub(r'<h1 class="title">.*?</h1>', "", body, flags=re.S)
    body = re.sub(r'<h2 class="author">.*?</h2>', "", body, flags=re.S)
    body = re.sub(r'<a class="anchor"[^>]*>#</a>', "", body)
    # The images are loaded directly (no lazy loading for the print)
    body = body.replace(' loading="lazy"', "")
    # The headings of the table of contents (chapters and sections)
    toc = []
    for m in re.finditer(r'<(h[12]) class="(Chapter|Section)" id="([^"]+)"><a class="toc" name="[^"]+">([^<]*)</a>(.*?)</\1>', body, re.S):
        toc.append((1 if m.group(2) == "Chapter" else 2, m.group(3), m.group(4).strip(), strip_tags(m.group(5))))
    return title, authors, body, toc


def page_html(title, authors, body, toc, pages=None):
    rows = []
    for level, hid, num, text in toc:
        p = str(pages.get(hid, "")) if pages else "000"
        rows.append('<li class="t%d"><a href="#%s"><span class="tn">%s</span><span class="tt">%s</span><span class="tp">%s</span></a></li>'
                    % (level, hid, html.escape(num), html.escape(text), p))
    version = re.search(r"Version\s+([\d.]+)", title)
    main_title = re.sub(r"\s*Version.*$", "", title)
    sub = re.search(r"\(([^)]*)\)", title)
    return TEMPLATE.replace("%TITLE%", html.escape(title)).replace("%MAINTITLE%", html.escape(main_title)) \
        .replace("%VERSION%", html.escape(version.group(1) if version else "")) \
        .replace("%SUB%", html.escape(sub.group(1) if sub else "")) \
        .replace("%AUTHORS%", "".join("<div>%s</div>" % html.escape(a) for a in authors)) \
        .replace("%TOC%", "\n".join(rows)).replace("%BODY%", body)


def print_pdf(page, pdf):
    folder = os.path.dirname(os.path.abspath(pdf))
    tmp = os.path.join(folder, ".print_tmp.html")
    open(tmp, "w", encoding="utf-8").write(page)
    profile = tempfile.mkdtemp(prefix="bio7pdf")
    try:
        subprocess.run([CHROME, "--headless=new", "--user-data-dir=" + profile, "--no-first-run", "--disable-gpu", "--no-pdf-header-footer",
                        "--generate-pdf-document-outline", "--virtual-time-budget=20000", "--print-to-pdf=" + os.path.abspath(pdf),
                        "file://" + tmp], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=600)
    finally:
        os.remove(tmp)


def heading_pages(pdf, toc):
    """The page numbers of the headings (from the bookmarks of the PDF, in the order of the document)"""
    try:
        import pypdf
    except ImportError:
        print("pypdf is not available: the table of contents has no page numbers (pip install pypdf)")
        return None
    reader = pypdf.PdfReader(pdf)
    marks = []

    def walk(items):
        for it in items:
            if isinstance(it, list):
                walk(it)
            else:
                marks.append((re.sub(r"\s+", " ", it.title).strip(), reader.get_destination_page_number(it) + 1))

    walk(reader.outline)
    pages, i = {}, 0
    for level, hid, num, text in toc:
        key = re.sub(r"\s", "", num + text)[:40]
        while i < len(marks) and not re.sub(r"\s", "", marks[i][0]).startswith(key):
            i += 1
        if i < len(marks):
            pages[hid] = marks[i][1]
            i += 1
    return pages


# ######################## The chapter tabs and the bookmarks ########################

TAB_TOP, TAB_HEIGHT, TAB_GAP, TAB_WIDTH, TAB_ACTIVE = 22.0, 17.6, 1.4, 7.0, 10.0  # mm


def tabs_html(page_count, chapter_of_page, chapters):
    """One overlay page for every page of the PDF: the tabs of the chapters at the right edge (the current chapter highlighted)"""
    pages = []
    for i in range(page_count):
        current = chapter_of_page[i]
        if current is None and i == 0:
            pages.append('<div class="p"></div>')
            continue
        tabs = []
        head = ""
        if current is not None:
            head = '<div class="head">%s &nbsp;\u00b7&nbsp; %s</div>' % (html.escape(chapters[current][0]), html.escape(chapters[current][1]))
        pages.append('<div class="p">%s%s</div>' % (head, "".join(tabs)))
    return """<!doctype html><html><head><meta charset="utf-8"><style>
@page { size: A4; margin: 0; }
html, body { margin: 0; background: transparent; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
.p { position: relative; width: 210mm; height: 297mm; break-after: page; overflow: hidden; }
.tab { position: absolute; right: 0; width: %.1fmm; height: %.1fmm; border-radius: 2.2mm 0 0 2.2mm; background: #e9edf3;
  font: 600 8pt -apple-system, "Helvetica Neue", Arial, sans-serif; color: #7a8290; display: flex; align-items: center; justify-content: center; }
.tab.on { width: %.1fmm; background: #1e66d0; color: #fff; font-size: 9pt; box-shadow: -0.6mm 0 1.5mm rgba(30,102,208,.35); }
.head { position: absolute; left: 17mm; top: 8.6mm; font: 8.5pt -apple-system, "Helvetica Neue", Arial, sans-serif; color: #9aa1ad; }
</style></head><body>%s</body></html>""" % (TAB_WIDTH, TAB_HEIGHT, TAB_ACTIVE, "".join(pages))


def finish(pdf, toc, pages):
    """Adds the running header (the chapter) and a bookmark tree which is displayed when the PDF is opened"""
    import pypdf
    from pypdf.annotations import Link
    from pypdf.generic import Fit
    chapters = [(num, text) for level, hid, num, text in toc if level == 1]
    starts = [pages.get(hid) for level, hid, num, text in toc if level == 1]
    reader = pypdf.PdfReader(pdf)
    n = len(reader.pages)
    chapter_of_page = []
    for i in range(n):
        current = None
        for k, st in enumerate(starts):
            if st and i + 1 >= st:
                current = k
        chapter_of_page.append(current)
    overlay_pdf = pdf + ".tabs.pdf"
    print_pdf(tabs_html(n, chapter_of_page, chapters), overlay_pdf)
    overlay = pypdf.PdfReader(overlay_pdf)
    writer = pypdf.PdfWriter(clone_from=reader)
    mm = 72 / 25.4
    for i in range(1, n):
        page = writer.pages[i]
        page.merge_page(overlay.pages[i])
    os.remove(overlay_pdf)
    # The bookmarks: the chapters (closed) with their sections, the titles with a space after the number
    old = reader.outline
    if "/Outlines" in writer._root_object:
        del writer._root_object["/Outlines"]

    def title_of(item):
        t = re.sub(r"\s+", " ", item.title).strip()
        return re.sub(r"^(\d+)(?=[A-Za-z])", r"\1 ", t)

    def add(items, parent, depth):
        last = None
        for it in items:
            if isinstance(it, list):
                if last is not None:
                    add(it, last, depth + 1)
                continue
            if depth == 0 and title_of(it) == strip_tags(TITLE_OF_COVER[0]):
                last = None
                continue
            top = it.get("/Top")
            fit = Fit.xyz(left=0, top=float(top)) if top is not None else Fit.fit()
            last = writer.add_outline_item(title_of(it), reader.get_destination_page_number(it), parent=parent, fit=fit,
                                           bold=depth == 0, is_open=False)
    add(old, None, 0)
    writer.page_mode = "/UseOutlines"
    writer.add_metadata({"/Title": TITLE_OF_COVER[0], "/Author": "M. Austenfeld"})
    with open(pdf, "wb") as f:
        writer.write(f)


TITLE_OF_COVER = [""]


TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>%TITLE%</title>
<style>
@page {
  size: A4;
  margin: 18mm 17mm 20mm 17mm;
  @bottom-center { content: counter(page); font: 9pt -apple-system, "Helvetica Neue", Arial, sans-serif; color: #7a8290; }
  @top-right { content: "Bio7 User Guide %VERSION%"; font: 8.5pt -apple-system, "Helvetica Neue", Arial, sans-serif; color: #9aa1ad; }
}
@page cover { margin: 0; @bottom-center { content: none; } @top-right { content: none; } }
@page toc { @top-right { content: none; } }
:root { --text: #1f2328; --muted: #5d6470; --border: #dfe3ea; --accent: #1e66d0; --soft: #f5f7fa; --code: #f3f5f8; }
* { box-sizing: border-box; }
html { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
body { margin: 0; color: var(--text); font: 10.2pt/1.55 -apple-system, BlinkMacSystemFont, "Helvetica Neue", Inter, Arial, sans-serif; }
a { color: var(--accent); text-decoration: none; }

/* The cover: the startup image of Bio7 on its background color */
.cover { page: cover; height: 297mm; width: 210mm; position: relative; overflow: hidden; color: #1f2b24; background: #f7f9f6; break-after: page; }
.cover .splash { position: absolute; top: 34mm; left: 8mm; width: 194mm; height: auto; }
.cover .text { position: absolute; left: 24mm; right: 24mm; top: 168mm; }
.cover .rule { width: 34mm; height: 1.4mm; background: #5aa832; border-radius: 1mm; margin-bottom: 7mm; }
.cover h1 { font-size: 34pt; line-height: 1.1; margin: 0 0 3mm; font-weight: 750; letter-spacing: -.4pt; color: #1f2b24; }
.cover .sub { font-size: 13pt; color: #5d6b62; margin: 0; }
.cover .authors { position: absolute; left: 24mm; right: 24mm; bottom: 24mm; font-size: 10.5pt; color: #5d6b62; line-height: 1.7; }
.cover .band { position: absolute; left: 0; right: 0; bottom: 0; height: 5mm; background: linear-gradient(90deg, #2f7a3b, #6cbf3c); }

/* The table of contents */
.contents { page: toc; break-after: page; }
.contents h1 { font-size: 24pt; margin: 0 0 8mm; }
.contents ul { list-style: none; margin: 0; padding: 0; }
.contents li a { display: flex; align-items: baseline; color: var(--text); }
.contents li.t1 { margin-top: 3.2mm; font-weight: 650; font-size: 11pt; }
.contents li.t2 { font-size: 9.8pt; color: var(--text); }
.contents li.t2 a { padding-left: 9mm; }
.contents .tn { min-width: 9mm; color: var(--muted); }
.contents li.t2 .tn { min-width: 11mm; }
.contents .tt { flex: 0 1 auto; }
.contents .tp { flex: 1 1 auto; min-width: 14mm; display: flex; align-items: baseline; justify-content: flex-end; font-variant-numeric: tabular-nums; }
.contents .tp::before { content: ""; flex: 1 1 auto; margin: 0 2mm; border-bottom: 1px dotted #b7bdc7; transform: translateY(-1mm); }
.contents li { break-inside: avoid; }

/* The content */
h1.Chapter { break-before: page; font-size: 25pt; line-height: 1.2; margin: 0 0 7mm; padding: 0 0 4mm; border-bottom: 2px solid var(--accent); }
h1.Chapter a.toc { display: block; font-size: 12pt; color: var(--accent); font-weight: 650; letter-spacing: .6pt; margin-bottom: 1mm; }
h1.Chapter a.toc::before { content: "CHAPTER "; }
h2.Section { font-size: 16pt; margin: 9mm 0 3mm; break-after: avoid; }
h3.Subsection, h3.Subsection- { font-size: 13pt; margin: 7mm 0 2mm; break-after: avoid; }
h4.Subsubsection { font-size: 11pt; margin: 5mm 0 1.5mm; break-after: avoid; }
h2 a.toc, h3 a.toc, h4 a.toc { color: var(--muted); margin-right: 2.5mm; font-weight: 600; }
.Indented, .Unindented { margin: 0 0 2.6mm; text-align: left; orphans: 3; widows: 3; }
ul, ol { padding-left: 6mm; margin: 1mm 0 3mm; }
li { margin: .8mm 0; }
.float { text-align: center; margin: 4mm 0 1mm; break-inside: avoid; }
.float + .caption, .caption { break-before: avoid; }
img.figure, img.embedded { max-width: 100% !important; width: auto !important; max-height: 205mm; height: auto; border-radius: 1.5mm; border: 1px solid var(--border); }
img[data-narrow] { max-width: 92mm !important; }
.caption { text-align: center; color: var(--muted); font-size: 8.8pt; margin: 1.5mm auto 5mm; max-width: 150mm; }
div.listing { margin: 3mm 0; break-inside: avoid; }
pre { background: var(--code); border: 1px solid var(--border); border-radius: 2mm; padding: 3mm 3.5mm; white-space: pre-wrap; word-break: break-word;
  font: 8.4pt/1.5 ui-monospace, "SF Mono", Menlo, Consolas, monospace; text-align: left; break-inside: avoid; }
pre .number-left { display: inline-block; width: 6mm; margin-right: 2mm; color: #9aa1ad; text-align: right; }
pre .copy { display: none; }
code, tt { font: .9em ui-monospace, "SF Mono", Menlo, Consolas, monospace; background: var(--code); padding: 0 1mm; border-radius: 1mm; }
table { border-collapse: collapse; margin: 2mm auto; font-size: 9pt; break-inside: auto; }
td, th { border: 1px solid var(--border); padding: 1.3mm 2.2mm; vertical-align: top; text-align: left; }
tr { break-inside: avoid; }
tr:first-child td { background: var(--soft); font-weight: 600; }
.medskip { height: 1mm; }
.biblio, .biblioentry { font-size: 9pt; }
</style>
</head>
<body>
<section class="cover">
  <img class="splash" src="images/chapter1/bio7_splash.png" alt="Bio7">
  <div class="text">
    <div class="rule"></div>
    <h1>User Guide</h1>
    <p class="sub">Version %VERSION% &nbsp;&middot;&nbsp; %SUB%</p>
  </div>
  <div class="authors">%AUTHORS%</div>
  <div class="band"></div>
</section>
<section class="contents">
  <h1>Contents</h1>
  <ul>
%TOC%
  </ul>
</section>
%BODY%
</body>
</html>
"""

if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else "Bio7_Manual.html"
    pdf = sys.argv[2] if len(sys.argv) > 2 else "Bio7_Manual.pdf"
    title, authors, body, toc = build(src)
    os.chdir(os.path.dirname(os.path.abspath(src)))
    print_pdf(page_html(title, authors, body, toc), pdf)
    pages = heading_pages(pdf, toc)
    if pages:
        print_pdf(page_html(title, authors, body, toc, pages), pdf)
        TITLE_OF_COVER[0] = re.sub(r"\s*Version.*$", "", title)
        finish(pdf, toc, pages)
    print("Created %s" % pdf)
