#!/usr/bin/env python3
"""
Creates a modern HTML version of the Bio7 manual from the eLyXer output.

Usage (in the folder of the manual):
    python3 /usr/local/bin/elyxer --mathjax remote --css bio7.css Main.lyx Main.html
    python3 modernize.py Main.html Bio7_Manual.html

The result is one HTML file (the styles and scripts are embedded, the images
are loaded from the images folder) with a table of contents in a sidebar
(the current section is highlighted), a full-text search, a light and a dark
theme, zoomable figures and copy buttons for the code listings. Only the
Python standard library is used.
"""

import html
import re
import sys


def strip_tags(s):
    return html.unescape(re.sub(r"<[^>]+>", "", s)).strip()


def remove_block(s, start_pattern):
    """Removes all <div ...> blocks which start with the pattern (balanced divs)"""
    while True:
        m = re.search(start_pattern, s)
        if not m:
            return s
        depth, i = 0, m.start()
        for t in re.finditer(r"<div\b|</div>", s[m.start():]):
            depth += 1 if t.group(0) == "<div" else -1
            if depth == 0:
                i = m.start() + t.end()
                break
        s = s[:m.start()] + s[i:]


def convert(src, dst):
    s = open(src, encoding="utf-8").read()
    title = strip_tags(re.search(r"<title>(.*?)</title>", s, re.S).group(1))
    body = s[s.index('<div id="globalWrapper">') + len('<div id="globalWrapper">'):s.rindex("</body>")]
    body = body[:body.rindex("</div>")]
    # MathJax of eLyXer (only a LyX macro, no formulas) and the warning
    body = re.sub(r'<script type="math/tex">.*?</script>', "", body, flags=re.S)
    body = re.sub(r"<noscript>.*?</noscript>", "", body, flags=re.S)
    # LyX commands which eLyXer doesn't know (newer LyX formats)
    body = re.sub(r"\\begin_inset Separator \w+\s*\\end_inset", "", body)
    body = body.replace("\\SpecialChar menuseparator", " \u25b8 ").replace("\\SpecialChar LaTeX", "LaTeX").replace("\\SpecialChar TeX", "TeX")
    # The table of contents of eLyXer (replaced by the sidebar)
    body = remove_block(body, r'<div class="fulltoc">')
    body = re.sub(r'<div class="tocheader">.*?</div>', "", body, flags=re.S)

    # The headings get ids and are collected for the sidebar
    toc = []

    def heading(m):
        tag, cls, name, number, rest = m.group(1), m.group(2), m.group(3), m.group(4), m.group(5)
        level = {"Chapter": 1, "Section": 2, "Subsection": 3, "Subsection-": 3, "Subsubsection": 4}[cls]
        text = strip_tags(rest)
        toc.append((level, name, number.strip(), text))
        return ('<%s class="%s" id="%s"><a class="toc" name="%s">%s</a> %s<a class="anchor" href="#%s" aria-label="Link">#</a></%s>'
                % (tag, cls, name, name, number, rest.strip(), name, tag))

    body = re.sub(r'<(h[1-4]) class="(Chapter|Section|Subsection-?|Subsubsection)">\s*<a class="toc" name="([^"]+)">([^<]*)</a>(.*?)</\1>',
                  heading, body, flags=re.S)

    # The images: lazy loading, the size of the eLyXer style is replaced by the CSS
    def image(m):
        tag = m.group(0)
        src = re.search(r'src="([^"]*)"', tag).group(1)
        w = re.search(r"max-width: (\d+)px", tag)
        tag = re.sub(r'\sstyle="[^"]*"', "", tag)
        if w:
            # The screenshots of the 3d perspective have the double resolution (Retina)
            width = int(w.group(1)) // (2 if "/chapter4/3d/" in src else 1)
            tag = tag.replace("<img ", '<img style="width: %dpx" ' % width, 1)
        extra = ' data-narrow="1"' if "/tab_" in src or "dialog" in src else ""
        return tag.replace("<img ", '<img loading="lazy" decoding="async"' + extra + " ", 1)

    body = re.sub(r"<img\b[^>]*>", image, body)

    # The sidebar: chapters with their sections (subsections are shown for the current chapter)
    nav, open_levels = [], []
    for level, name, number, text in toc:
        if level > 3:
            continue
        nav.append('<li class="l%d"><a href="#%s" data-id="%s"><span class="num">%s</span>%s</a></li>'
                   % (level, name, name, html.escape(number), html.escape(text)))
    nav_html = "\n".join(nav)

    page = TEMPLATE.replace("%TITLE%", html.escape(title)).replace("%NAV%", nav_html).replace("%BODY%", body)
    open(dst, "w", encoding="utf-8").write(page)
    print("Created %s (%d headings)" % (dst, len(toc)))


TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>%TITLE%</title>
<script>
/* The theme before the first paint (light, dark or the system setting) */
try { var t = localStorage.getItem('bio7-manual-theme'); if (t) document.documentElement.setAttribute('data-theme', t); } catch (e) {}
</script>
<style>
:root {
  --bg: #ffffff; --bg-soft: #f6f7f9; --bg-code: #f3f4f6; --text: #1f2328; --muted: #5d6470; --border: #e1e4e8;
  --accent: #1e66d0; --accent-soft: rgba(30, 102, 208, .10); --mark: #ffe58a; --shadow: 0 1px 3px rgba(0,0,0,.08), 0 4px 16px rgba(0,0,0,.06);
  --sidebar: 300px; --header: 56px;
  color-scheme: light;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg: #16181d; --bg-soft: #1d2027; --bg-code: #20242c; --text: #e6e8ec; --muted: #9aa3b2; --border: #2e333d;
    --accent: #6aa6ff; --accent-soft: rgba(106, 166, 255, .14); --mark: #6b5a12; --shadow: 0 1px 3px rgba(0,0,0,.4), 0 4px 16px rgba(0,0,0,.3);
    color-scheme: dark;
  }
}
:root[data-theme="dark"] {
  --bg: #16181d; --bg-soft: #1d2027; --bg-code: #20242c; --text: #e6e8ec; --muted: #9aa3b2; --border: #2e333d;
  --accent: #6aa6ff; --accent-soft: rgba(106, 166, 255, .14); --mark: #6b5a12; --shadow: 0 1px 3px rgba(0,0,0,.4), 0 4px 16px rgba(0,0,0,.3);
  color-scheme: dark;
}
* { box-sizing: border-box; }
html { scroll-padding-top: calc(var(--header) + 16px); }
body { margin: 0; overflow-x: hidden; background: var(--bg); color: var(--text); font: 16px/1.65 -apple-system, BlinkMacSystemFont, "Segoe UI", Inter, Roboto, "Helvetica Neue", Arial, sans-serif; }
a { color: var(--accent); text-decoration: none; }
a:hover { text-decoration: underline; }

/* Header */
header { position: fixed; inset: 0 0 auto 0; height: var(--header); display: flex; align-items: center; gap: 12px; padding: 0 16px;
  background: color-mix(in srgb, var(--bg) 88%, transparent); backdrop-filter: blur(10px); border-bottom: 1px solid var(--border); z-index: 20; }
header .brand { font-weight: 700; font-size: 17px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; color: var(--text); }
header .brand small { font-weight: 500; color: var(--muted); margin-left: 6px; }
header .spacer { flex: 1; }
.icon-btn { border: 1px solid var(--border); background: var(--bg-soft); color: var(--text); width: 36px; height: 36px; border-radius: 8px; cursor: pointer;
  display: inline-flex; align-items: center; justify-content: center; font-size: 16px; }
.icon-btn:hover { border-color: var(--accent); }
#menu { display: none; }
.search { position: relative; width: min(420px, 45vw); }
.search input { width: 100%; height: 36px; border-radius: 8px; border: 1px solid var(--border); background: var(--bg-soft); color: var(--text);
  padding: 0 12px 0 34px; font: inherit; font-size: 14px; outline: none; }
.search input:focus { border-color: var(--accent); box-shadow: 0 0 0 3px var(--accent-soft); }
.search svg { position: absolute; left: 10px; top: 10px; width: 16px; height: 16px; fill: var(--muted); }
.search kbd { position: absolute; right: 8px; top: 8px; font: 12px ui-monospace, Menlo, monospace; color: var(--muted); border: 1px solid var(--border);
  border-radius: 4px; padding: 0 5px; background: var(--bg); }
#results { position: absolute; top: 42px; left: 0; right: 0; max-height: 70vh; overflow: auto; background: var(--bg); border: 1px solid var(--border);
  border-radius: 10px; box-shadow: var(--shadow); display: none; padding: 6px; }
#results a { display: block; padding: 8px 10px; border-radius: 6px; color: var(--text); }
#results a:hover, #results a.sel { background: var(--accent-soft); text-decoration: none; }
#results .rt { font-weight: 600; font-size: 14px; }
#results .rs { font-size: 13px; color: var(--muted); }
#results mark, main mark { background: var(--mark); color: inherit; border-radius: 2px; }
#results .none { padding: 10px; color: var(--muted); font-size: 14px; }

/* Sidebar */
nav#toc { position: fixed; top: var(--header); bottom: 0; left: 0; width: var(--sidebar); overflow: auto; padding: 16px 10px 40px 14px;
  border-right: 1px solid var(--border); background: var(--bg-soft); font-size: 14px; z-index: 10; }
nav#toc ul { list-style: none; margin: 0; padding: 0; }
nav#toc a { display: flex; gap: 8px; padding: 4px 8px; border-radius: 6px; color: var(--text); line-height: 1.35; }
nav#toc a:hover { background: var(--accent-soft); text-decoration: none; }
nav#toc a.active { background: var(--accent-soft); color: var(--accent); font-weight: 600; }
nav#toc .num { color: var(--muted); min-width: 2.4em; font-variant-numeric: tabular-nums; }
nav#toc .l1 { margin-top: 10px; }
nav#toc .l1 > a { font-weight: 650; }
nav#toc .l2 a { padding-left: 18px; }
nav#toc .l3 a { padding-left: 32px; font-size: 13px; }
nav#toc .l3 { display: none; }
nav#toc .l3.show { display: block; }

/* Content */
main { margin-left: var(--sidebar); padding: calc(var(--header) + 24px) 48px 80px; }
.content { max-width: 920px; margin: 0 auto; }
h1.title { font-size: 34px; line-height: 1.2; margin: 8px 0 4px; }
h2.author { font-size: 15px; font-weight: 500; color: var(--muted); margin: 0; }
h1.Chapter { font-size: 30px; line-height: 1.25; margin: 64px 0 16px; padding-top: 24px; border-top: 1px solid var(--border); }
h2.Section { font-size: 24px; line-height: 1.3; margin: 44px 0 12px; }
h3.Subsection, h3.Subsection- { font-size: 19px; margin: 32px 0 8px; }
h4.Subsubsection { font-size: 16.5px; margin: 26px 0 6px; }
h1 a.toc, h2 a.toc, h3 a.toc, h4 a.toc { color: var(--muted); font-weight: 600; margin-right: 6px; }
a.anchor { opacity: 0; margin-left: 8px; color: var(--muted); font-weight: 400; }
h1:hover a.anchor, h2:hover a.anchor, h3:hover a.anchor, h4:hover a.anchor { opacity: 1; text-decoration: none; }
.Indented, .Unindented { margin: 0 0 12px; }
.Indented { text-indent: 0; }
ul, ol { padding-left: 24px; }
li { margin: 4px 0; }
.float { margin: 20px 0 6px; text-align: center; }
img.figure, img.embedded { max-width: 100%; height: auto; border-radius: 8px; box-shadow: var(--shadow); cursor: zoom-in; background: var(--bg-soft); }
img[data-narrow] { max-width: min(100%, 460px); }
.caption { text-align: center; color: var(--muted); font-size: 14px; margin: 6px auto 22px; max-width: 760px; }
div.listing { margin: 14px 0; }
pre.listing, pre { position: relative; background: var(--bg-code); border: 1px solid var(--border); border-radius: 10px; padding: 14px 16px; overflow: auto;
  font: 13.5px/1.55 ui-monospace, "SF Mono", Menlo, Consolas, "Liberation Mono", monospace; text-align: left; }
pre .number-left { display: inline-block; width: 2.2em; margin-right: 10px; color: var(--muted); text-align: right; user-select: none; opacity: .6; }
code, tt, .code { font: 0.9em ui-monospace, "SF Mono", Menlo, Consolas, monospace; background: var(--bg-code); padding: 1px 5px; border-radius: 4px; }
.copy { position: absolute; top: 8px; right: 8px; font: 12px -apple-system, sans-serif; border: 1px solid var(--border); background: var(--bg); color: var(--muted);
  border-radius: 6px; padding: 3px 8px; cursor: pointer; opacity: 0; transition: opacity .15s; }
pre:hover .copy, .copy:focus { opacity: 1; }
table { border-collapse: collapse; margin: 10px auto; font-size: 14.5px; max-width: 100%; display: block; overflow-x: auto; }
td, th { border: 1px solid var(--border); padding: 6px 10px; vertical-align: top; text-align: left; }
tr:first-child td { background: var(--bg-soft); }
.medskip { height: 6px; }
.biblio, .biblioentry { font-size: 14px; }
.Description { margin: 6px 0; }

/* Back to the top, lightbox */
#top { position: fixed; right: 20px; bottom: 20px; opacity: 0; pointer-events: none; transition: opacity .2s; z-index: 15; }
#top.show { opacity: 1; pointer-events: auto; }
#lightbox { position: fixed; inset: 0; background: rgba(0,0,0,.82); display: none; align-items: center; justify-content: center; z-index: 50; cursor: zoom-out; padding: 24px; }
#lightbox img { max-width: 96vw; max-height: 92vh; border-radius: 8px; box-shadow: 0 10px 40px rgba(0,0,0,.6); }
#lightbox.show { display: flex; }

@media (max-width: 960px) {
  #menu { display: inline-flex; }
  nav#toc { transform: translateX(-100%); transition: transform .2s; width: min(86vw, 340px); box-shadow: var(--shadow); }
  body.nav-open nav#toc { transform: none; }
  main { margin-left: 0; padding: calc(var(--header) + 16px) 16px 64px; }
  header .brand small { display: none; }
  .search { width: auto; flex: 1; min-width: 0; }
  .search input { min-width: 0; }
  header { gap: 8px; padding: 0 12px; }
  header .brand { flex-shrink: 0; }
  header .spacer { display: none; }
  .search kbd { display: none; }
}
@media print {
  header, nav#toc, #top { display: none; }
  main { margin: 0; padding: 0; }
  img.figure { box-shadow: none; }
}
</style>
</head>
<body>
<header>
  <button class="icon-btn" id="menu" aria-label="Contents">&#9776;</button>
  <div class="brand">Bio7 Manual<small>%TITLE%</small></div>
  <div class="spacer"></div>
  <div class="search">
    <svg viewBox="0 0 24 24"><path d="M10 2a8 8 0 1 0 4.9 14.3l5.4 5.4 1.4-1.4-5.4-5.4A8 8 0 0 0 10 2zm0 2a6 6 0 1 1 0 12 6 6 0 0 1 0-12z"/></svg>
    <input id="q" type="search" placeholder="Search the manual" autocomplete="off" aria-label="Search">
    <kbd>/</kbd>
    <div id="results"></div>
  </div>
  <button class="icon-btn" id="theme" aria-label="Theme" title="Light / dark theme">&#9680;</button>
</header>
<nav id="toc"><ul>
%NAV%
</ul></nav>
<main><div class="content">
%BODY%
</div></main>
<button class="icon-btn" id="top" aria-label="Back to the top">&#8593;</button>
<div id="lightbox"><img alt=""></div>
<script>
(function () {
  var root = document.documentElement, body = document.body;
  /* Theme: light, dark (stored) or the system setting */
  document.getElementById('theme').addEventListener('click', function () {
    var dark = root.getAttribute('data-theme') ? root.getAttribute('data-theme') === 'dark' : matchMedia('(prefers-color-scheme: dark)').matches;
    var t = dark ? 'light' : 'dark';
    root.setAttribute('data-theme', t);
    try { localStorage.setItem('bio7-manual-theme', t); } catch (e) {}
  });
  document.getElementById('menu').addEventListener('click', function () { body.classList.toggle('nav-open'); });

  /* The sidebar: the current section is highlighted, the subsections of the current chapter are shown */
  var links = [].slice.call(document.querySelectorAll('nav#toc a'));
  var byId = {}; links.forEach(function (a) { byId[a.getAttribute('data-id')] = a; });
  var heads = [].slice.call(document.querySelectorAll('main h1[id], main h2[id], main h3[id]'));
  var current = null;
  function chapterOf(li) { while (li && !li.classList.contains('l1')) li = li.previousElementSibling; return li; }
  function setActive(id) {
    var a = byId[id]; if (!a || a === current) return;
    if (current) current.classList.remove('active');
    current = a; a.classList.add('active');
    var chap = chapterOf(a.parentNode);
    [].slice.call(document.querySelectorAll('nav#toc li.l3')).forEach(function (li) { li.classList.toggle('show', chapterOf(li) === chap); });
    var nav = document.getElementById('toc'), r = a.getBoundingClientRect(), n = nav.getBoundingClientRect();
    if (r.top < n.top + 40 || r.bottom > n.bottom - 40) nav.scrollTop += r.top - n.top - n.height / 3;
  }
  function onScroll() {
    var y = 90, id = heads.length ? heads[0].id : null;
    for (var i = 0; i < heads.length; i++) { if (heads[i].getBoundingClientRect().top <= y) id = heads[i].id; else break; }
    if (id) setActive(id);
    document.getElementById('top').classList.toggle('show', scrollY > 800);
  }
  /* At most every 80 ms and once after the scrolling */
  var last = 0, timer = null;
  addEventListener('scroll', function () {
    var now = Date.now(); clearTimeout(timer);
    if (now - last > 80) { last = now; onScroll(); }
    timer = setTimeout(onScroll, 100);
  }, { passive: true });
  addEventListener('load', function () { setTimeout(onScroll, 50); });
  addEventListener('hashchange', function () { setTimeout(onScroll, 50); });
  onScroll();
  links.forEach(function (a) { a.addEventListener('click', function () { body.classList.remove('nav-open'); }); });
  document.getElementById('top').addEventListener('click', function () { scrollTo({ top: 0, behavior: 'smooth' }); });

  /* Copy buttons of the listings (without the line numbers) */
  [].slice.call(document.querySelectorAll('pre')).forEach(function (pre) {
    var b = document.createElement('button'); b.className = 'copy'; b.textContent = 'Copy';
    b.addEventListener('click', function () {
      var c = pre.cloneNode(true); [].slice.call(c.querySelectorAll('.number-left, .copy')).forEach(function (e) { e.remove(); });
      navigator.clipboard.writeText(c.textContent.replace(/\n$/, '')).then(function () { b.textContent = 'Copied'; setTimeout(function () { b.textContent = 'Copy'; }, 1200); });
    });
    pre.appendChild(b);
  });

  /* Lightbox of the figures */
  var lb = document.getElementById('lightbox'), lbImg = lb.querySelector('img');
  document.addEventListener('click', function (e) {
    var t = e.target;
    if (t.tagName === 'IMG' && t.closest('main')) { lbImg.src = t.currentSrc || t.src; lb.classList.add('show'); }
  });
  lb.addEventListener('click', function () { lb.classList.remove('show'); });

  /* The full-text search: the sections (heading and text up to the next heading) */
  var sections = [];
  var all = [].slice.call(document.querySelectorAll('main h1[id], main h2[id], main h3[id], main h4[id]'));
  all.forEach(function (h, i) {
    var text = '', n = h.nextSibling, next = all[i + 1];
    while (n && n !== next) {
      if (n.nodeType === 1 && next && n.contains(next)) break;
      text += ' ' + (n.textContent || ''); n = n.nextSibling;
    }
    var title = h.textContent.replace('#', '').trim();
    sections.push({ id: h.id, title: title, text: text.replace(/\s+/g, ' '), lower: (title + ' ' + text).toLowerCase() });
  });
  var q = document.getElementById('q'), res = document.getElementById('results'), sel = -1;
  function esc(s) { return s.replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function hl(s, words) { var r = esc(s); words.forEach(function (w) { r = r.replace(new RegExp('(' + w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + ')', 'ig'), '<mark>$1</mark>'); }); return r; }
  function search() {
    var v = q.value.trim().toLowerCase(); sel = -1;
    if (v.length < 2) { res.style.display = 'none'; return; }
    var words = v.split(/\s+/).filter(Boolean), hits = [];
    sections.forEach(function (s) {
      if (!words.every(function (w) { return s.lower.indexOf(w) >= 0; })) return;
      var score = words.reduce(function (a, w) { return a + (s.title.toLowerCase().indexOf(w) >= 0 ? 10 : 0) + (s.lower.split(w).length - 1); }, 0);
      hits.push({ s: s, score: score });
    });
    hits.sort(function (a, b) { return b.score - a.score; });
    res.innerHTML = hits.length ? hits.slice(0, 30).map(function (h) {
      var t = h.s.text, i = t.toLowerCase().indexOf(words[0]), snip = i < 0 ? t.slice(0, 140) : (i > 60 ? '…' : '') + t.slice(Math.max(0, i - 60), i + 100) + '…';
      return '<a href="#' + h.s.id + '" data-w="' + esc(v) + '"><div class="rt">' + hl(h.s.title, words) + '</div><div class="rs">' + hl(snip, words) + '</div></a>';
    }).join('') : '<div class="none">No results</div>';
    res.style.display = 'block';
  }
  function markIn(id, words) {
    [].slice.call(document.querySelectorAll('main mark.found')).forEach(function (m) { m.replaceWith(document.createTextNode(m.textContent)); });
    var h = document.getElementById(id); if (!h) return;
    var n = h, end = all[all.indexOf(h) + 1], first = null;
    var re = new RegExp(words.map(function (w) { return w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); }).join('|'), 'ig');
    while (n && n !== end) {
      if (n.nodeType === 1 && end && n.contains(end)) break;
      var walker = document.createTreeWalker(n, NodeFilter.SHOW_TEXT), nodes = [], t;
      while ((t = walker.nextNode())) nodes.push(t);
      if (n.nodeType === 3) nodes = [n];
      nodes.forEach(function (tn) {
        if (!tn.parentNode || tn.parentNode.closest('script,style,pre .number-left')) return;
        var s = tn.nodeValue; re.lastIndex = 0; if (!re.test(s)) return;
        var f = document.createDocumentFragment(), last = 0; re.lastIndex = 0; var m;
        while ((m = re.exec(s))) { f.appendChild(document.createTextNode(s.slice(last, m.index))); var mk = document.createElement('mark'); mk.className = 'found'; mk.textContent = m[0]; f.appendChild(mk); if (!first) first = mk; last = m.index + m[0].length; }
        f.appendChild(document.createTextNode(s.slice(last))); tn.parentNode.replaceChild(f, tn);
      });
      n = n.nextSibling;
    }
    (first || h).scrollIntoView({ block: first ? 'center' : 'start' });
  }
  q.addEventListener('input', search);
  q.addEventListener('focus', search);
  res.addEventListener('click', function (e) {
    var a = e.target.closest('a'); if (!a) return; e.preventDefault();
    res.style.display = 'none'; history.replaceState(null, '', a.getAttribute('href'));
    markIn(a.getAttribute('href').slice(1), a.getAttribute('data-w').split(/\s+/));
  });
  q.addEventListener('keydown', function (e) {
    var items = [].slice.call(res.querySelectorAll('a'));
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      e.preventDefault(); sel = Math.max(0, Math.min(items.length - 1, sel + (e.key === 'ArrowDown' ? 1 : -1)));
      items.forEach(function (a, i) { a.classList.toggle('sel', i === sel); }); if (items[sel]) items[sel].scrollIntoView({ block: 'nearest' });
    } else if (e.key === 'Enter' && items.length) { (items[sel < 0 ? 0 : sel]).click(); }
    else if (e.key === 'Escape') { q.value = ''; res.style.display = 'none'; q.blur(); }
  });
  document.addEventListener('keydown', function (e) {
    if (e.key === '/' && document.activeElement !== q) { e.preventDefault(); q.focus(); }
    if (e.key === 'Escape') lb.classList.remove('show');
  });
  document.addEventListener('click', function (e) { if (!e.target.closest('.search')) res.style.display = 'none'; });
})();
</script>
</body>
</html>
"""

if __name__ == "__main__":
    convert(sys.argv[1] if len(sys.argv) > 1 else "Main.html", sys.argv[2] if len(sys.argv) > 2 else "Bio7_Manual.html")
