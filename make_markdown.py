#!/usr/bin/env python3
"""
Creates a Markdown version of the Bio7 manual (e.g., for GitHub) from the modern
HTML version (see modernize.py): a folder with a README.md (the title and the
table of contents), one Markdown file for every chapter and the images which
are used by the manual.

Usage (in the folder of the manual, after build.sh):
    python3 make_markdown.py Bio7_Manual.html markdown
or in the folder of the manual itself (e.g., the root of a Git repository: the
README.md is the start page, the images of the manual are used directly):
    python3 make_markdown.py Bio7_Manual.html .
With --single the whole manual is written into the README.md (one file, e.g.,
the start page of a GitHub repository):
    python3 make_markdown.py Bio7_Manual.html . --single

Needs pandoc (https://pandoc.org) and the Python package beautifulsoup4.
"""

import os
import re
import shutil
import subprocess
import sys
import unicodedata

from bs4 import BeautifulSoup, NavigableString


def slug(text, used):
    """The anchor of a heading on GitHub (lower case, without punctuation, spaces to hyphens, numbered duplicates)"""
    s = unicodedata.normalize("NFKC", text).strip().lower()
    s = re.sub(r"[^\w\- ]", "", s)
    s = s.replace(" ", "-")
    base, n = s, 1
    while s in used:
        s = "%s-%d" % (base, n)
        n += 1
    used.add(s)
    return s


def file_name(number, title):
    t = re.sub(r"[^A-Za-z0-9]+", "-", title).strip("-")
    return "%02d-%s.md" % (int(number), t) if number.isdigit() else t + ".md"


def language(code):
    if re.search(r"\b(public|import|new [A-Z]\w*\(|double\[\]|String\[\])", code) and ";" in code:
        return "java"
    if "<-" in code or re.search(r"\b(library|data\.frame|summary|lm)\(", code):
        return "r"
    if re.search(r"^\s*(def |import |print\()", code, re.M):
        return "python"
    return ""


def convert(src, out, single=False):
    soup = BeautifulSoup(open(src, encoding="utf-8").read(), "html.parser")
    content = soup.select_one("main .content")
    title = content.select_one("h1.title").get_text(" ", strip=True)
    authors = [a.get_text(" ", strip=True) for a in content.select("h2.author")]
    for e in content.select("h1.title, h2.author, a.anchor, .copy"):
        e.decompose()

    # The chapters (the content before the first chapter is the introduction of the README)
    nodes = list(content.children)
    chapters, intro, current = [], [], None
    for n in nodes:
        if getattr(n, "name", None) == "h1" and "Chapter" in (n.get("class") or []):
            num = n.select_one("a.toc").get_text(strip=True)
            text = n.get_text(" ", strip=True)[len(num):].strip()
            current = {"num": num, "title": text, "nodes": [n]}
            chapters.append(current)
        elif current is None:
            intro.append(n)
        else:
            current["nodes"].append(n)
    for c in chapters:
        c["file"] = "README.md" if single else file_name(c["num"], c["title"])

    # The anchors: the headings (GitHub slugs) and the labels (to the heading of their section)
    anchors = {}
    # One file: the anchors are unique in the file (the title and the contents come first)
    shared = set()
    if single:
        slug(title, shared)
        slug("Contents", shared)
    for c in chapters:
        used = shared if single else set()
        last = None
        for n in c["nodes"]:
            if isinstance(n, NavigableString):
                continue
            for e in ([n] if n.name in ("h1", "h2", "h3", "h4") else []) + n.find_all(["h1", "h2", "h3", "h4", "a"]):
                if e.name in ("h1", "h2", "h3", "h4"):
                    last = c["file"] + "#" + slug(e.get_text(" ", strip=True), used)
                    if e.get("id"):
                        anchors[e["id"]] = last
                    for a in e.find_all("a"):
                        if a.get("name"):
                            anchors[a["name"]] = last
                elif e.get("name") and last:
                    anchors.setdefault(e["name"], last)
        c["anchor"] = c["file"]

    images = set()
    codes = []

    def prepare(nodes):
        """The HTML of a chapter for pandoc: figures with captions, code blocks, tables with a header, links between the files"""
        wrap = BeautifulSoup("<div></div>", "html.parser")
        root = wrap.div
        for n in nodes:
            root.append(n.extract() if not isinstance(n, NavigableString) else NavigableString(str(n)))
        for a in root.select("a.toc"):
            # The numbers of the headings are kept (the anchors of GitHub contain them)
            if a.find_parent(["h1", "h2", "h3", "h4"]) and a.get_text(strip=True):
                a.replace_with(NavigableString(a.get_text(strip=True) + " "))
            else:
                a.decompose()
        for a in root.select("a.Label"):
            a.decompose()
        for a in root.find_all("a", href=True):
            h = a["href"]
            if h.startswith("#"):
                target = anchors.get(h[1:])
                if target:
                    a["href"] = target
                else:
                    a.unwrap()
        for f in root.select("div.float"):
            img = f.find("img")
            cap = f.find("div", class_="caption") or f.find_next_sibling("div", class_="caption")
            caption = cap.get_text(" ", strip=True) if cap else ""
            if img:
                srcs = img.get("src", "")
                images.add(srcs)
                new = BeautifulSoup('<p><img src="%s" alt="%s"></p>' % (srcs, caption.replace('"', "'")), "html.parser")
                if cap:
                    new.append(BeautifulSoup("<p><em>%s</em></p>" % cap.decode_contents().strip(), "html.parser"))
                f.replace_with(new)
        for img in root.find_all("img"):
            images.add(img.get("src", ""))
            for k in list(img.attrs):
                if k not in ("src", "alt"):
                    del img[k]
            if img.get("alt", "").startswith("figure "):
                img["alt"] = os.path.splitext(os.path.basename(img.get("src", "")))[0].replace("_", " ")
        for pre in root.find_all("pre"):
            for s in pre.select(".number-left"):
                s.decompose()
            code = pre.get_text().replace("\u200b", "")
            # A placeholder, the fenced code block (with the language) is inserted after pandoc
            codes.append("```" + language(code) + "\n" + code.rstrip("\n") + "\n```")
            new = wrap.new_tag("p")
            new.string = "BIO7CODEBLOCK%d" % (len(codes) - 1)
            pre.replace_with(new)
        for t in root.find_all("table"):
            rows = t.find_all("tr")
            if rows and not t.find("th"):
                for td in rows[0].find_all("td"):
                    td.name = "th"
                thead = wrap.new_tag("thead")
                rows[0].wrap(thead)
        return str(root)

    def pandoc(html):
        r = subprocess.run(["pandoc", "-f", "html", "-t", "gfm", "--wrap=none"], input=html, capture_output=True, text=True, check=True)
        md = r.stdout
        md = re.sub(r"<div[^>]*>|</div>", "", md)
        md = re.sub(r"<span[^>]*>|</span>", "", md)
        md = re.sub(r"\n{3,}", "\n\n", md)
        md = re.sub(r"^BIO7CODEBLOCK(\d+)$", lambda m: codes[int(m.group(1))], md, flags=re.M)
        return md.strip() + "\n"

    os.makedirs(out, exist_ok=True)
    nav = lambda i: ("\n\n---\n\n" + " | ".join(filter(None, [
        "[← %s](%s)" % (chapters[i - 1]["title"], chapters[i - 1]["file"]) if i > 0 else "",
        "[Contents](README.md)",
        "[%s →](%s)" % (chapters[i + 1]["title"], chapters[i + 1]["file"]) if i + 1 < len(chapters) else ""])) + "\n")
    chapter_md = []
    for i, c in enumerate(chapters):
        md = pandoc(prepare(c["nodes"]))
        if single:
            chapter_md.append(md + "\n[\u2191 Contents](#contents)\n")
        else:
            open(os.path.join(out, c["file"]), "w", encoding="utf-8").write(md + nav(i))

    # The README: the title, the introduction and the table of contents
    readme = ["# " + title, ""]
    readme += ["*" + " · ".join(authors) + "*", ""] if authors else []
    readme.append(pandoc(prepare(intro)))
    readme += ["## Contents", ""]
    for c in chapters:
        readme.append("%s. [%s](%s)" % (c["num"], c["title"], c["file"]))
        for n in c["nodes"]:
            if getattr(n, "name", None) == "h2":
                pass
    toc_html = BeautifulSoup(open(src, encoding="utf-8").read(), "html.parser")
    lines = ["## Contents", ""]
    for li in toc_html.select("nav#toc li"):
        a = li.find("a"); level = int(li["class"][0][1:])
        if level > 2:
            continue
        target = anchors.get(a["data-id"], "")
        num = a.select_one(".num").get_text(strip=True); text = a.get_text(" ", strip=True)[len(num):].strip()
        lines.append(("" if level == 1 else "   ") + "- [%s %s](%s)" % (num, text, target))
    readme = readme[:readme.index("## Contents")] + lines
    # The startup image of Bio7 below the title
    text = "\n".join(readme)
    m = re.search(r"\n(!\[[^\]]*\]\(images/chapter1/bio7_splash\.png\))\n", text)
    if m:
        text = text.replace(m.group(0), "\n", 1).replace("# " + title + "\n", "# " + title + "\n\n" + m.group(1) + "\n", 1)
    readme = text.split("\n")
    if single:
        for md in chapter_md:
            readme += ["", "---", "", md.rstrip("\n")]
    # A link to the description of the build (if the folder contains a BUILD.md)
    if os.path.exists(os.path.join(out, "BUILD.md")):
        readme += ["", "---", "", "The manual is written in LyX, see [BUILD.md](BUILD.md) for the sources and the build of the HTML, PDF and Markdown versions."]
    open(os.path.join(out, "README.md"), "w", encoding="utf-8").write("\n".join(readme) + "\n")

    # The images used by the manual
    n = 0
    for s in sorted(images):
        if not s or s.startswith("http"):
            continue
        dst = os.path.join(out, s)
        if os.path.abspath(dst) == os.path.abspath(s):
            # The Markdown is written next to the images (e.g., the root of a repository)
            n += 1
            continue
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if os.path.exists(s):
            shutil.copy2(s, dst)
            n += 1
    print("Created %s: README.md, %d chapters, %d images" % (out, len(chapters), n))


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else "Bio7_Manual.html"
    out = sys.argv[2] if len(sys.argv) > 2 else "markdown"
    single = "--single" in sys.argv
    os.chdir(os.path.dirname(os.path.abspath(src)))
    convert(os.path.basename(src), out, single)
