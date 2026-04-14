#!/usr/bin/env python3
"""
ogsm_to_html.py — Convert OGSM markdown spec to a styled HTML page.

Parses agent sections from OGSM markdown files and generates a complete
HTML page with collapsible <details> blocks for each agent's full G/S/M/Anti-patterns.

Usage:
    python3 ogsm_to_html.py <input.md> <output.html> [--lang zh|en] [--title "..."] [--copilot]

Pure Python 3 stdlib only (re, html, pathlib, argparse, datetime).
"""

import re
import html
import argparse
import sys
from pathlib import Path
from datetime import datetime


# ── Parsing helpers ──────────────────────────────────────────────────────

def read_file(path: str) -> str:
    """Read a file with UTF-8 encoding."""
    return Path(path).read_text(encoding="utf-8")


def extract_metadata(text: str) -> dict:
    """Extract top-level metadata (Course Code, Version, Created, Updated, Owner)."""
    meta = {}
    for key in ("Course Code", "Document Type", "Version", "Created", "Updated", "Owner", "Supersedes"):
        m = re.search(rf"\*\*{re.escape(key)}:\*\*\s*(.+)", text)
        if m:
            meta[key] = m.group(1).strip()
    # Extract the top-level title (first # heading)
    m = re.search(r"^#\s+(.+)", text, re.MULTILINE)
    if m:
        meta["title"] = m.group(1).strip()
    return meta


def extract_objective(text: str) -> str:
    """Extract the O — Objective section content."""
    m = re.search(r"^## O — Objective\s*\n(.*?)(?=^## |\Z)", text, re.MULTILINE | re.DOTALL)
    if m:
        return m.group(1).strip()
    return ""


def extract_team_structure(text: str) -> str:
    """Extract the Team Structure section content."""
    m = re.search(r"^## Team Structure\s*\n(.*?)(?=^## |\Z)", text, re.MULTILINE | re.DOTALL)
    if m:
        return m.group(1).strip()
    return ""


def find_agent_sections(text: str) -> list:
    """
    Find all agent sections starting with ### EMOJI AgentName.
    Returns list of (header, body) tuples.
    """
    # Find the "Individual OGSM Definitions" section first
    start_match = re.search(r"^## Individual OGSM Definitions", text, re.MULTILINE)
    if not start_match:
        # Fall back: just find all ### with emoji
        search_text = text
    else:
        search_text = text[start_match.start():]

    # Split on ### headings that contain emoji (Unicode range check)
    pattern = r"^### (.+)$"
    headers = list(re.finditer(pattern, search_text, re.MULTILINE))

    agents = []
    for i, hm in enumerate(headers):
        header_text = hm.group(1).strip()
        # Check if this header contains an emoji (common emoji ranges)
        if not re.search(r"[\U0001F300-\U0001FAFF\u2600-\u27BF\u2700-\u27BF\u231A-\u23FA\u25AA-\u25FF\uFE0F\u200D\u2702-\u27B0\u2764\u2712\u270D\u270F\u2611\u2601-\u260F]", header_text):
            continue
        start = hm.end()
        # Find end: next ### header or end of text
        if i + 1 < len(headers):
            end = headers[i + 1].start()
        else:
            end = len(search_text)
        body = search_text[start:end].strip()
        # Only include sections that have a G block (real agents, not reclassification notes)
        if "**G（" in body or "**Tier 1" in body:
            agents.append((header_text, body))

    return agents


def parse_agent(header: str, body: str) -> dict:
    """Parse an agent section into structured data."""
    agent = {"header": header, "raw_body": body}

    # Extract emoji and name
    m = re.match(r"([\U0001F300-\U0001FAFF\u2600-\u27BF\u2700-\u27BF\u231A-\u23FA\u25AA-\u25FF]+)\s*(.*)", header)
    if m:
        agent["emoji"] = m.group(1)
        agent["name"] = m.group(2).strip()
    else:
        agent["emoji"] = ""
        agent["name"] = header

    # Extract blocks using ** headers
    def extract_block(label_pattern: str) -> str:
        """Extract content between a **label** header and the next **header** or ---."""
        pat = re.compile(
            rf"^\*\*{label_pattern}.*?\*\*\s*\n(.*?)(?=^\*\*[A-Z\u4e00-\u9fff]|\n---|\Z)",
            re.MULTILINE | re.DOTALL
        )
        m2 = pat.search(body)
        if m2:
            return m2.group(1).strip()
        return ""

    agent["g_block"] = extract_block(r"G（")
    agent["tier1_block"] = extract_block(r"Tier 1")
    agent["s_block"] = extract_block(r"S（")
    agent["m_block"] = extract_block(r"M（")
    agent["antipatterns_block"] = extract_block(r"Anti-patterns")
    agent["alignment_block"] = extract_block(r"對齊 O")

    # Extract model commands from Tier 1
    mc = re.search(r"\*\*Model commands\*\*[：:]\s*(.+)", body)
    agent["model_commands"] = mc.group(1).strip() if mc else ""

    # Extract skill commands from Tier 1
    sc = re.search(r"\*\*Skill commands\*\*[：:]\s*(.+)", body)
    agent["skill_commands"] = sc.group(1).strip() if sc else ""

    return agent


def detect_model_badges(model_commands: str) -> list:
    """Detect model types from Model commands line and return badge info."""
    badges = []
    text = model_commands.lower()
    if "claude" in text or "native" in text or "opus" in text:
        badges.append(("claude", "Claude"))
    if "gemini" in text or "flash" in text:
        badges.append(("gemini", "Gemini"))
    if "codex" in text:
        badges.append(("codex", "Codex"))
    if "ai-collab" in text or "ai_collab" in text:
        # Extract task type
        tm = re.search(r"--task\s+(\w+)", model_commands)
        if tm:
            task_type = tm.group(1)
            # Map task types to models
            task_model_map = {
                "research": ("gemini", "Gemini"),
                "verify": ("gemini", "Gemini"),
                "persona": ("gemini", "Gemini"),
                "seo": ("gemini", "Gemini"),
                "code": ("codex", "Codex"),
                "review": ("codex", "Codex"),
                "html-build": ("codex", "Codex"),
            }
            if task_type in task_model_map:
                badge = task_model_map[task_type]
                if badge not in badges:
                    badges.append(badge)
    return badges


# ── Markdown to HTML conversion helpers ──────────────────────────────────

def md_inline(text: str) -> str:
    """Convert inline markdown to HTML (bold, code, links)."""
    t = html.escape(text)
    # Bold
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    # Code
    t = re.sub(r"`(.+?)`", r"<code>\1</code>", t)
    # Links
    t = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', t)
    return t


def md_block_to_html(block: str) -> str:
    """Convert a markdown block (with bullets, blockquotes, paragraphs) to HTML."""
    if not block:
        return ""

    lines = block.split("\n")
    out = []
    in_list = False
    in_blockquote = False

    for line in lines:
        stripped = line.strip()
        if not stripped:
            if in_list:
                out.append("</ul>")
                in_list = False
            if in_blockquote:
                out.append("</blockquote>")
                in_blockquote = False
            continue

        # Blockquote
        if stripped.startswith(">"):
            content = stripped.lstrip("> ").strip()
            if not in_blockquote:
                if in_list:
                    out.append("</ul>")
                    in_list = False
                out.append("<blockquote>")
                in_blockquote = True
            out.append(f"<p>{md_inline(content)}</p>")
            continue
        elif in_blockquote:
            # Continuation of blockquote (no > prefix but still part of it)
            if stripped and not stripped.startswith("-") and not stripped.startswith("*"):
                out.append(f"<p>{md_inline(stripped)}</p>")
                continue
            else:
                out.append("</blockquote>")
                in_blockquote = False

        # Bullet list
        if re.match(r"^[-*]\s", stripped):
            if not in_list:
                out.append("<ul>")
                in_list = True
            content = re.sub(r"^[-*]\s+", "", stripped)
            out.append(f"<li>{md_inline(content)}</li>")
            continue
        elif stripped.startswith("  ") and in_list:
            # Continuation of previous bullet (indented)
            if out and out[-1].endswith("</li>"):
                prev = out[-1]
                out[-1] = prev[:-5] + " " + md_inline(stripped) + "</li>"
            continue

        # Numbered list
        if re.match(r"^\d+\.\s", stripped):
            if in_list:
                out.append("</ul>")
                in_list = False
            content = re.sub(r"^\d+\.\s+", "", stripped)
            out.append(f"<p>{md_inline(content)}</p>")
            continue

        # Regular paragraph
        if in_list:
            out.append("</ul>")
            in_list = False
        out.append(f"<p>{md_inline(stripped)}</p>")

    if in_list:
        out.append("</ul>")
    if in_blockquote:
        out.append("</blockquote>")

    return "\n".join(out)


def md_table_to_html(text: str) -> str:
    """Convert markdown tables in text to HTML tables."""
    lines = text.split("\n")
    result = []
    table_lines = []
    in_table = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("|") and stripped.endswith("|"):
            # Skip separator lines
            if re.match(r"^\|[\s\-:]+\|$", stripped):
                continue
            table_lines.append(stripped)
            in_table = True
        else:
            if in_table:
                result.append(render_table(table_lines))
                table_lines = []
                in_table = False
            result.append(line)

    if in_table:
        result.append(render_table(table_lines))

    return "\n".join(result)


def render_table(lines: list) -> str:
    """Render collected table lines to HTML."""
    if not lines:
        return ""
    rows = []
    for i, line in enumerate(lines):
        cells = [c.strip() for c in line.strip("|").split("|")]
        tag = "th" if i == 0 else "td"
        cells_html = "".join(f"<{tag}>{md_inline(c)}</{tag}>" for c in cells)
        rows.append(f"<tr>{cells_html}</tr>")
    return f'<table>\n{"".join(rows)}\n</table>'


# ── HTML generation ──────────────────────────────────────────────────────

CSS = """\
:root {
  --primary: #222; --accent: #edd144; --accent-hover: #b79310;
  --bg: #fff; --bg-alt: #f7f7f7; --border: #dbe2ea;
  --text: #333; --text-light: #666; --highlight: #fff9e0;
  --factory: #0ea5e9; --factory-bg: #f0f9ff; --factory-border: #bae6fd;
  --claude: #7c3aed; --claude-bg: #f5f3ff; --claude-border: #c4b5fd;
  --codex: #059669; --codex-bg: #ecfdf5; --codex-border: #a7f3d0;
  --gemini: #2563eb; --gemini-bg: #eff6ff; --gemini-border: #93c5fd;
}
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: "Source Sans Pro", -apple-system, sans-serif; color: var(--text); line-height: 1.8; max-width: 900px; margin: 0 auto; padding: 2rem 2.5rem; font-size: 17px; }
header { border-bottom: 2px solid var(--accent); padding-bottom: 1rem; margin-bottom: 2rem; }
.site-name { font-size: 1.5rem; font-weight: 700; color: var(--primary); }
.site-name span { color: var(--text-light); font-weight: 400; font-size: 0.9rem; }
nav { margin-top: 0.5rem; }
nav a { color: var(--primary); text-decoration: none; margin-right: 1.2rem; font-size: 0.95rem; font-weight: 600; }
h1 { font-size: 1.8rem; color: var(--primary); margin-bottom: 0.5rem; }
h2 { font-size: 1.3rem; color: var(--primary); margin: 2rem 0 0.8rem; border-bottom: 2px solid var(--accent); padding-bottom: 0.3rem; }
h3 { font-size: 1.1rem; color: var(--primary); margin: 1.5rem 0 0.5rem; }
p { margin-bottom: 0.7rem; }
ul, ol { padding-left: 1.5rem; margin: 0.3rem 0 0.7rem; }
li { margin-bottom: 0.3rem; }
a { color: var(--primary); font-weight: 600; }
.breadcrumb { font-size: 0.85rem; color: var(--text-light); margin-bottom: 1rem; }
.breadcrumb a { color: var(--text-light); font-weight: 400; text-decoration: none; }
.article-meta { font-size: 0.85rem; color: var(--text-light); margin-bottom: 1.5rem; }
code { background: var(--bg-alt); padding: 0.15rem 0.4rem; border-radius: 3px; font-size: 0.85em; }
.banner { background: var(--factory-bg); border: 1px solid var(--factory-border); border-left: 4px solid var(--factory); border-radius: 8px; padding: 1rem 1.2rem; margin: 1.5rem 0; }
blockquote { background: var(--highlight); border-left: 4px solid var(--accent); padding: 0.8rem 1rem; margin: 0.7rem 0; font-style: italic; }
table { width: 100%; border-collapse: collapse; margin: 1rem 0; font-size: 0.95rem; }
th, td { border: 1px solid var(--border); padding: 0.5rem 0.8rem; text-align: left; }
th { background: var(--bg-alt); font-weight: 700; }
.agent-card { border: 1px solid var(--border); border-radius: 8px; margin: 1.2rem 0; padding: 1rem 1.2rem; background: var(--bg); }
.agent-card h3 { font-size: 1.1rem; margin-bottom: 0.5rem; color: var(--primary); }
.agent-card ul { font-size: 0.95rem; }
.agent-card li { margin-bottom: 0.25rem; }
.badge { display: inline-block; border-radius: 4px; padding: 0.1rem 0.5rem; font-size: 0.75rem; font-weight: 600; margin-right: 0.3rem; vertical-align: middle; }
.badge-claude { background: var(--claude-bg); border: 1px solid var(--claude-border); color: var(--claude); }
.badge-codex { background: var(--codex-bg); border: 1px solid var(--codex-border); color: var(--codex); }
.badge-gemini { background: var(--gemini-bg); border: 1px solid var(--gemini-border); color: var(--gemini); }
details { margin-top: 0.5rem; }
details summary { cursor: pointer; font-weight: 600; color: var(--primary); font-size: 0.95rem; padding: 0.3rem 0; }
details summary:hover { color: var(--accent-hover); }
details[open] summary { margin-bottom: 0.5rem; }
.detail-section { margin: 0.8rem 0; padding: 0.5rem 0; border-top: 1px solid var(--border); }
.detail-section h4 { font-size: 1rem; color: var(--primary); margin-bottom: 0.4rem; }
footer { border-top: 2px solid var(--accent); padding-top: 1rem; margin-top: 3rem; font-size: 0.85rem; color: var(--text-light); text-align: center; }
"""


def generate_badge_html(badges: list) -> str:
    """Generate HTML for model badges."""
    parts = []
    for cls, label in badges:
        parts.append(f'<span class="badge badge-{cls}">{label}</span>')
    return " ".join(parts)


def generate_agent_card(agent: dict, copilot: bool = False) -> str:
    """Generate HTML for one agent card with Tier 1 visible and details collapsed."""
    badges_html = ""
    if copilot and agent["model_commands"]:
        badges = detect_model_badges(agent["model_commands"])
        if badges:
            badges_html = " " + generate_badge_html(badges)

    # Tier 1 content
    tier1_html = md_block_to_html(agent["tier1_block"])

    # Full details sections
    details_parts = []

    if agent["g_block"]:
        details_parts.append(f'''<div class="detail-section">
<h4>G (Goal)</h4>
{md_block_to_html(agent["g_block"])}
</div>''')

    if agent["s_block"]:
        details_parts.append(f'''<div class="detail-section">
<h4>S (Strategy)</h4>
{md_block_to_html(agent["s_block"])}
</div>''')

    if agent["m_block"]:
        details_parts.append(f'''<div class="detail-section">
<h4>M (Measure)</h4>
{md_block_to_html(agent["m_block"])}
</div>''')

    if agent["antipatterns_block"]:
        details_parts.append(f'''<div class="detail-section">
<h4>Anti-patterns</h4>
{md_block_to_html(agent["antipatterns_block"])}
</div>''')

    if agent["alignment_block"]:
        details_parts.append(f'''<div class="detail-section">
<h4>O Alignment</h4>
{md_block_to_html(agent["alignment_block"])}
</div>''')

    details_inner = "\n".join(details_parts)

    return f'''<div class="agent-card">
<h3>{html.escape(agent["header"])}{badges_html}</h3>
{tier1_html}
<details>
<summary>Full G / S / M / Anti-patterns</summary>
{details_inner}
</details>
</div>'''


def generate_html(
    metadata: dict,
    objective: str,
    team_structure: str,
    agents: list,
    title: str,
    lang: str,
    copilot: bool,
    input_path: str,
    line_count: int,
) -> str:
    """Generate the complete HTML page."""
    lang_attr = "zh-Hant" if lang == "zh" else "en"

    # Labels
    if lang == "zh":
        lbl_overview = "概覽"
        lbl_objective = "O — Objective (目標)"
        lbl_team = "Team Structure (團隊結構)"
        lbl_agents = "Individual OGSM Definitions"
        lbl_total = "個 agent"
        lbl_gen = "由 ogsm_to_html.py 自動產生"
        lbl_banner_file = "來源檔案"
        lbl_banner_lines = "行"
        lbl_banner_agents = "個 agent"
        lbl_banner_date = "產生日期"
    else:
        lbl_overview = "Overview"
        lbl_objective = "O — Objective"
        lbl_team = "Team Structure"
        lbl_agents = "Individual OGSM Definitions"
        lbl_total = "agents"
        lbl_gen = "Generated by ogsm_to_html.py"
        lbl_banner_file = "Source file"
        lbl_banner_lines = "lines"
        lbl_banner_agents = "agents"
        lbl_banner_date = "Generated"

    version = metadata.get("Version", "")
    input_filename = Path(input_path).name
    today = datetime.now().strftime("%Y-%m-%d")

    # Banner
    banner_html = f'''<div class="banner">
<strong>{lbl_overview}</strong>: {lbl_banner_file}: <code>{html.escape(input_filename)}</code> |
{line_count} {lbl_banner_lines} | {len(agents)} {lbl_banner_agents} |
{lbl_banner_date}: {today}
</div>'''

    # Objective section
    obj_html = ""
    if objective:
        obj_content = md_table_to_html(objective)
        obj_html = f'''<h2>{lbl_objective}</h2>
{md_block_to_html(obj_content)}'''

    # Team structure section
    team_html = ""
    if team_structure:
        team_content = md_table_to_html(team_structure)
        team_html = f'''<h2>{lbl_team}</h2>
{team_content}'''

    # Agent cards
    agent_cards = "\n".join(generate_agent_card(a, copilot) for a in agents)

    page_title = title if title else metadata.get("title", "OGSM Spec")

    return f'''<!DOCTYPE html>
<html lang="{lang_attr}">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{html.escape(page_title)} | watersonusa.ai</title>
  <meta name="robots" content="noindex">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Source+Sans+Pro:wght@400;600;700&display=swap" rel="stylesheet">
  <style>
{CSS}
  </style>
</head>
<body>

<header>
  <div class="site-name">watersonusa.ai <span>/ blog / zh</span></div>
  <nav>
    <a href="/blog/zh/claude-code-memory-skill-architecture/">Series</a>
    <a href="/blog/zh/">All articles</a>
    <a href="/">Home</a>
  </nav>
</header>

<h1>{html.escape(page_title)}</h1>
<p class="article-meta">{html.escape(version)} | {len(agents)} {lbl_total} | {lbl_gen}</p>

{banner_html}

{obj_html}

{team_html}

<h2>{lbl_agents}</h2>
{agent_cards}

<footer>
  <p>{lbl_gen} | {today} | watersonusa.ai</p>
</footer>

</body>
</html>
'''


# ── Main ─────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Convert OGSM markdown spec to styled HTML page."
    )
    parser.add_argument("input", help="Path to input OGSM markdown file")
    parser.add_argument("output", help="Path to output HTML file")
    parser.add_argument("--lang", choices=["zh", "en"], default="zh",
                        help="Page chrome language (default: zh)")
    parser.add_argument("--title", default="",
                        help="Custom page title (default: extracted from markdown)")
    parser.add_argument("--copilot", action="store_true",
                        help="Enable model badge coloring based on Model commands")

    args = parser.parse_args()

    # Read input
    text = read_file(args.input)
    line_count = text.count("\n") + 1

    # Parse
    metadata = extract_metadata(text)
    objective = extract_objective(text)
    team_structure = extract_team_structure(text)
    raw_agents = find_agent_sections(text)

    if not raw_agents:
        print(f"ERROR: No agent sections found in {args.input}", file=sys.stderr)
        sys.exit(1)

    agents = [parse_agent(h, b) for h, b in raw_agents]

    # Generate HTML
    html_content = generate_html(
        metadata=metadata,
        objective=objective,
        team_structure=team_structure,
        agents=agents,
        title=args.title,
        lang=args.lang,
        copilot=args.copilot,
        input_path=args.input,
        line_count=line_count,
    )

    # Write output
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html_content, encoding="utf-8")

    # Report
    details_count = html_content.count("<details>")
    print(f"OK: {len(agents)} agents | {line_count} input lines | {details_count} <details> blocks")
    print(f"    Output: {args.output}")
    for a in agents:
        badges = detect_model_badges(a["model_commands"]) if args.copilot else []
        badge_str = " ".join(f"[{b[1]}]" for b in badges) if badges else ""
        print(f"    - {a['emoji']} {a['name']} {badge_str}")


if __name__ == "__main__":
    main()
