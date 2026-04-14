#!/usr/bin/env python3
import argparse
import html
import re
import sys
from pathlib import Path

CSS = """body{margin:0;background:#f6f3ee;color:#1f2933;font:20px/1.75 "Source Sans Pro","Segoe UI",sans-serif}main{max-width:920px;margin:0 auto;padding:48px 24px 80px}header{margin-bottom:36px;padding-bottom:20px;border-bottom:1px solid #d7d0c6}.eyebrow{color:#8a5a44;font-size:.92rem;letter-spacing:.08em;text-transform:uppercase}h1,h2,h3,h4,h5,h6{line-height:1.2;margin:1.5em 0 .55em;color:#16202a}h1{font-size:2.8rem;margin-top:.2em}h2{font-size:2rem}h3{font-size:1.5rem}p,ul,ol,blockquote,pre{margin:1em 0}ul,ol{padding-left:1.5em}li+li{margin-top:.35em}blockquote{margin-left:0;padding:.2em 0 .2em 1em;border-left:4px solid #c97f5d;background:rgba(201,127,93,.08);color:#5f4b3a}code{padding:.1em .3em;border-radius:4px;background:#efe7dc;font-family:Consolas,monospace}pre{overflow:auto;padding:16px 18px;border-radius:10px;background:#1f2430;color:#e9eef5}pre code{padding:0;background:transparent;color:inherit}a{color:#8a3b12}footer{margin-top:48px;color:#6b7280;font-size:.95rem}"""
CHROME = {
    "en": ("Blog Post", "Generated from Markdown."),
    "zh": ("部落格文章", "由 Markdown 轉換產生。"),
}


def parse_args():
    p = argparse.ArgumentParser(description="Convert markdown into a styled HTML blog page.")
    p.add_argument("input")
    p.add_argument("output")
    p.add_argument("--title")
    p.add_argument("--lang", default="en", choices=["en", "zh"])
    return p.parse_args()


def slugify(text):
    base = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE).strip().lower()
    return re.sub(r"[-\s]+", "-", base) or "section"


def inline(text):
    text = html.escape(text, quote=False)
    patterns = [
        (r"`([^`]+)`", r"<code>\1</code>"),
        (r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>'),
        (r"\*\*([^*]+)\*\*", r"<strong>\1</strong>"),
        (r"\*([^*]+)\*", r"<em>\1</em>"),
    ]
    for pat, repl in patterns:
        text = re.sub(pat, repl, text)
    return text


def render_markdown(text):
    out, para, quote, items, ids = [], [], [], [], set()
    title = desc = ""
    list_tag = None
    code = None

    def flush_para():
        nonlocal para, desc
        if not para:
            return
        content = " ".join(x.strip() for x in para).strip()
        if content:
            desc = desc or re.sub(r"\s+", " ", content)
            out.append(f"<p>{inline(content)}</p>")
        para = []

    def flush_list():
        nonlocal items, list_tag
        if items:
            out.append(f"<{list_tag}>")
            out.extend(f"<li>{inline(x)}</li>" for x in items)
            out.append(f"</{list_tag}>")
        items, list_tag = [], None

    def flush_quote():
        nonlocal quote
        if quote:
            out.append(f"<blockquote><p>{inline(' '.join(quote).strip())}</p></blockquote>")
        quote = []

    def flush_all():
        flush_para()
        flush_list()
        flush_quote()

    for raw in text.splitlines() + [""]:
        line = raw.rstrip("\n")
        stripped = line.strip()
        if stripped.startswith("```"):
            flush_all()
            if code is None:
                code = []
            else:
                out.append(f"<pre><code>{html.escape(chr(10).join(code))}</code></pre>")
                code = None
            continue
        if code is not None:
            code.append(line)
            continue
        if not stripped:
            flush_all()
            continue
        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m:
            flush_all()
            level, text = len(m.group(1)), m.group(2).strip()
            if level == 1 and not title:
                title = re.sub(r"[*_`]+", "", text).strip()
            anchor = slugify(text)
            n = 2
            while anchor in ids:
                anchor = f"{slugify(text)}-{n}"
                n += 1
            ids.add(anchor)
            out.append(f'<h{level} id="{anchor}">{inline(text)}</h{level}>')
            continue
        m = re.match(r"^>\s?(.*)$", line)
        if m:
            flush_para()
            flush_list()
            quote.append(m.group(1).strip())
            continue
        um = re.match(r"^[-*]\s+(.*)$", line)
        om = re.match(r"^\d+\.\s+(.*)$", line)
        if um or om:
            flush_para()
            flush_quote()
            tag = "ol" if om else "ul"
            if list_tag and list_tag != tag:
                flush_list()
            list_tag = tag
            items.append((om or um).group(1))
            continue
        para.append(line)

    return "\n".join(out), title, desc


def build_html(title, desc, body, lang):
    eyebrow, footer = CHROME[lang]
    page_lang = "zh-Hant" if lang == "zh" else "en"
    t, d = html.escape(title), html.escape(desc)
    return f"""<!doctype html>
<html lang="{page_lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{t}</title>
<meta name="description" content="{d}">
<meta property="og:type" content="article">
<meta property="og:title" content="{t}">
<meta property="og:description" content="{d}">
<link rel="alternate" hreflang="en" href="#">
<link rel="alternate" hreflang="zh-Hant" href="#">
<link rel="alternate" hreflang="x-default" href="#">
<style>{CSS}</style>
</head>
<body>
<main>
<header>
<div class="eyebrow">{eyebrow}</div>
<h1>{t}</h1>
</header>
{body}
<footer>{footer}</footer>
</main>
</body>
</html>
"""


def main():
    args = parse_args()
    src = Path(args.input).read_text(encoding="utf-8")
    body, found_title, desc = render_markdown(src)
    title = args.title or found_title or Path(args.input).stem.replace("_", " ").title()
    desc = (desc or title)[:200]
    Path(args.output).write_text(build_html(title, desc, body, args.lang), encoding="utf-8")


if __name__ == "__main__":
    try:
        main()
    except FileNotFoundError as exc:
        print(f"File not found: {exc.filename}", file=sys.stderr)
        sys.exit(1)
