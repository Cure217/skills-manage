#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import re
from pathlib import Path
from typing import Any


THEMES = {
    "dark": {
        "body_bg": "#0b1120",
        "body_bg_2": "#101934",
        "panel": "rgba(17, 25, 46, 0.9)",
        "text": "#eef4ff",
        "muted": "#a9b6d3",
        "line": "rgba(149, 173, 255, 0.18)",
        "hero": "rgba(11, 17, 33, 0.94)",
        "chip": "rgba(122, 178, 255, 0.10)",
        "quote_bg": "rgba(125, 231, 255, 0.08)",
        "quote_line": "#7de7ff",
    },
    "light": {
        "body_bg": "#f4f7ff",
        "body_bg_2": "#eaf0ff",
        "panel": "rgba(255, 255, 255, 0.92)",
        "text": "#14213d",
        "muted": "#51607d",
        "line": "rgba(86, 108, 164, 0.18)",
        "hero": "rgba(255, 255, 255, 0.96)",
        "chip": "rgba(86, 128, 217, 0.08)",
        "quote_bg": "rgba(86, 128, 217, 0.08)",
        "quote_line": "#5680d9",
    },
}

CARD_TONES = {
    "default": ("rgba(255,255,255,0.03)", "rgba(149,173,255,0.14)"),
    "good": ("rgba(117,224,167,0.08)", "rgba(117,224,167,0.22)"),
    "warn": ("rgba(255,190,122,0.08)", "rgba(255,190,122,0.22)"),
    "danger": ("rgba(255,147,204,0.08)", "rgba(255,147,204,0.22)"),
}


def esc(value: Any) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def render_text(text: Any) -> str:
    return esc(text).replace("\n", "<br>")


def render_meta(meta: list[dict[str, Any]]) -> str:
    if not meta:
        return ""
    cards = []
    for item in meta:
        label = render_text(item.get("label", ""))
        value = render_text(item.get("value", ""))
        cards.append(
            f"""
            <div class="meta-card">
              <div class="meta-label">{label}</div>
              <div class="meta-value">{value}</div>
            </div>
            """
        )
    return f'<div class="meta-grid">{"".join(cards)}</div>'


def render_tldr(items: list[Any]) -> str:
    if not items:
        return ""
    lis = "".join(f"<li>{render_text(item)}</li>" for item in items)
    return f"""
    <section class="section">
      <h2>TL;DR</h2>
      <ul>{lis}</ul>
    </section>
    """


def render_cards(items: list[dict[str, Any]]) -> str:
    cards = []
    for item in items:
        tone = item.get("tone", "default")
        bg, border = CARD_TONES.get(tone, CARD_TONES["default"])
        cards.append(
            f"""
            <div class="mini-card" style="background:{bg};border-color:{border}">
              <h3>{render_text(item.get("title", ""))}</h3>
              <p>{render_text(item.get("body", ""))}</p>
            </div>
            """
        )
    return f'<div class="grid cards-grid">{"".join(cards)}</div>'


def render_bullets(items: list[Any]) -> str:
    lis = "".join(f"<li>{render_text(item)}</li>" for item in items)
    return f"<ul>{lis}</ul>"


def render_numbered(items: list[Any]) -> str:
    lis = "".join(f"<li>{render_text(item)}</li>" for item in items)
    return f"<ol>{lis}</ol>"


def render_timeline(items: list[dict[str, Any]]) -> str:
    blocks = []
    for item in items:
        blocks.append(
            f"""
            <div class="timeline-item">
              <h3>{render_text(item.get("title", ""))}</h3>
              <p>{render_text(item.get("body", ""))}</p>
            </div>
            """
        )
    return f'<div class="timeline">{"".join(blocks)}</div>'


def render_quote(text: Any) -> str:
    return f'<div class="quote">{render_text(text)}</div>'


def render_checklist(items: list[Any]) -> str:
    rows = []
    status_map = {
        "done": "已完成",
        "completed": "已完成",
        "in_progress": "进行中",
        "progress": "进行中",
        "pending": "待处理",
        "blocked": "阻塞",
    }
    for raw in items:
        if isinstance(raw, dict):
            title = render_text(raw.get("title", ""))
            detail = render_text(raw.get("detail", ""))
            status_key = str(raw.get("status", "pending")).lower()
        else:
            title = render_text(raw)
            detail = ""
            status_key = "pending"
        status_text = status_map.get(status_key, status_key)
        rows.append(
            f"""
            <div class="check-item">
              <div class="check-main">
                <span class="status-badge status-{esc(status_key)}">{render_text(status_text)}</span>
                <div class="check-text">
                  <div class="check-title">{title}</div>
                  {f"<div class='check-detail'>{detail}</div>" if detail else ""}
                </div>
              </div>
            </div>
            """
        )
    return f'<div class="checklist">{"".join(rows)}</div>'


def render_callout(block: dict[str, Any]) -> str:
    tone = block.get("tone", "default")
    title = block.get("title")
    text = block.get("text", "")
    return f"""
    <div class="callout tone-{esc(tone)}">
      {f"<div class='callout-title'>{render_text(title)}</div>" if title else ""}
      <div class="callout-body">{render_text(text)}</div>
    </div>
    """


def render_kv(items: list[dict[str, Any]]) -> str:
    rows = []
    for item in items:
        rows.append(
            f"""
            <div class="row">
              <div class="k">{render_text(item.get("key", ""))}</div>
              <div class="v">{render_text(item.get("value", ""))}</div>
            </div>
            """
        )
    return f'<div class="table-like">{"".join(rows)}</div>'


def render_table(block: dict[str, Any]) -> str:
    columns = block.get("columns", [])
    rows = block.get("rows", [])
    if not columns:
        return ""
    head = "".join(f"<th>{render_text(col)}</th>" for col in columns)
    body_rows = []
    for row in rows:
        if isinstance(row, dict):
            values = [row.get(str(col), "") for col in columns]
        else:
            values = list(row)
        tds = "".join(f"<td>{render_text(value)}</td>" for value in values)
        body_rows.append(f"<tr>{tds}</tr>")
    return f"""
    <div class="table-wrap">
      <table class="summary-table">
        <thead><tr>{head}</tr></thead>
        <tbody>{''.join(body_rows)}</tbody>
      </table>
    </div>
    """


def render_subsections(items: list[dict[str, Any]]) -> str:
    parts = []
    for item in items:
        blocks = "".join(render_block(block) for block in item.get("blocks", []))
        parts.append(
            f"""
            <div class="subsection-card">
              <h3>{render_text(item.get("title", ""))}</h3>
              {f"<p class='sub-lead'>{render_text(item.get('lead', ''))}</p>" if item.get('lead') else ""}
              {blocks}
            </div>
            """
        )
    return f'<div class="subsections">{"".join(parts)}</div>'


def sanitize_filename_stem(text: str) -> str:
    invalid_chars = set('<>:"/\\|?*')
    cleaned = "".join("-" if ch in invalid_chars or ord(ch) < 32 else ch for ch in text)
    cleaned = cleaned.strip().strip(".")
    cleaned = re.sub(r"\s+", "-", cleaned)
    cleaned = re.sub(r"-{2,}", "-", cleaned)
    if not cleaned:
        return "conversation-summary"
    return cleaned[:80]


def render_block(block: dict[str, Any]) -> str:
    block_type = block.get("type", "paragraph")
    if block_type == "paragraph":
        return f'<p>{render_text(block.get("text", ""))}</p>'
    if block_type == "bullets":
        return render_bullets(block.get("items", []))
    if block_type == "numbered":
        return render_numbered(block.get("items", []))
    if block_type == "timeline":
        return render_timeline(block.get("items", []))
    if block_type == "cards":
        return render_cards(block.get("items", []))
    if block_type == "quote":
        return render_quote(block.get("text", ""))
    if block_type == "checklist":
        return render_checklist(block.get("items", []))
    if block_type == "callout":
        return render_callout(block)
    if block_type == "kv":
        return render_kv(block.get("items", []))
    if block_type == "table":
        return render_table(block)
    if block_type == "subsections":
        return render_subsections(block.get("items", []))
    return f'<p>{render_text(block.get("text", f"[Unsupported block type: {block_type}]"))}</p>'


def render_sections(sections: list[dict[str, Any]]) -> tuple[str, str]:
    toc_links: list[str] = []
    html_sections: list[str] = []
    for index, section in enumerate(sections, start=1):
        title = section.get("title", f"Section {index}")
        anchor = section.get("id") or f"section-{index}"
        toc_links.append(f'<a href="#{esc(anchor)}">{index}. {render_text(title)}</a>')
        lead = section.get("lead")
        blocks = "".join(render_block(block) for block in section.get("blocks", []))
        html_sections.append(
            f"""
            <section class="section" id="{esc(anchor)}">
              <h2>{render_text(title)}</h2>
              {"<p class='lead'>" + render_text(lead) + "</p>" if lead else ""}
              {blocks}
            </section>
            """
        )
    return "".join(toc_links), "".join(html_sections)


def build_html(data: dict[str, Any], theme_name: str, source_name: str) -> str:
    theme = THEMES[theme_name]
    title = data.get("title") or "Conversation Summary"
    subtitle = data.get("subtitle") or ""
    toc_links, section_html = render_sections(data.get("sections", []))
    meta_html = render_meta(data.get("meta", []))
    tldr_html = render_tldr(data.get("tldr", []))
    generated_at = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{esc(title)}</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
      color: {theme["text"]};
      background:
        radial-gradient(circle at top left, rgba(122, 178, 255, 0.12), transparent 28%),
        radial-gradient(circle at top right, rgba(184, 155, 255, 0.12), transparent 22%),
        linear-gradient(180deg, {theme["body_bg"]} 0%, {theme["body_bg_2"]} 100%);
      line-height: 1.7;
    }}
    .shell {{
      max-width: 1280px;
      margin: 0 auto;
      padding: 28px 22px 72px;
    }}
    .hero, .toc, .section {{
      border: 1px solid {theme["line"]};
      background: {theme["panel"]};
      border-radius: 22px;
      box-shadow: 0 18px 42px rgba(0,0,0,0.18);
      backdrop-filter: blur(10px);
    }}
    .hero {{
      background: {theme["hero"]};
      padding: 30px 28px 24px;
      margin-bottom: 20px;
    }}
    .eyebrow {{
      display: inline-flex;
      padding: 7px 12px;
      border-radius: 999px;
      border: 1px solid {theme["line"]};
      background: {theme["chip"]};
      color: {theme["muted"]};
      font-size: 13px;
      margin-bottom: 12px;
    }}
    h1 {{
      margin: 0 0 10px;
      font-size: 38px;
      line-height: 1.16;
    }}
    p, li {{ color: {theme["muted"]}; font-size: 14px; }}
    .hero p {{ margin: 0; font-size: 15px; }}
    .meta-grid {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 12px;
      margin-top: 20px;
    }}
    .meta-card {{
      border: 1px solid {theme["line"]};
      background: rgba(255,255,255,0.03);
      border-radius: 16px;
      padding: 13px 14px;
    }}
    .meta-label {{ font-size: 12px; color: {theme["muted"]}; margin-bottom: 4px; text-transform: uppercase; letter-spacing: .08em; }}
    .meta-value {{ font-size: 14px; font-weight: 600; color: {theme["text"]}; }}
    .layout {{
      display: grid;
      grid-template-columns: 280px minmax(0, 1fr);
      gap: 20px;
      align-items: start;
    }}
    .toc {{
      position: sticky;
      top: 18px;
      padding: 18px;
    }}
    .toc h2, .section h2 {{
      margin: 0 0 10px;
      color: {theme["text"]};
    }}
    .toc a {{
      display: block;
      color: {theme["muted"]};
      text-decoration: none;
      padding: 8px 10px;
      border-radius: 10px;
      font-size: 14px;
    }}
    .toc a:hover {{ background: {theme["chip"]}; color: {theme["text"]}; }}
    .content {{ display: grid; gap: 16px; }}
    .section {{
      padding: 22px 22px 18px;
    }}
    .lead {{ margin: 0 0 14px; font-size: 14px; }}
    .grid {{
      display: grid;
      gap: 12px;
    }}
    .cards-grid {{
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    }}
    .mini-card {{
      border: 1px solid {theme["line"]};
      border-radius: 16px;
      padding: 14px;
    }}
    .mini-card h3 {{
      margin: 0 0 8px;
      font-size: 16px;
      color: {theme["text"]};
    }}
    ul, ol {{ margin: 10px 0 0 20px; padding: 0; }}
    li + li {{ margin-top: 6px; }}
    .timeline {{
      position: relative;
      display: grid;
      gap: 14px;
      margin-top: 8px;
    }}
    .timeline::before {{
      content: "";
      position: absolute;
      left: 12px;
      top: 8px;
      bottom: 8px;
      width: 2px;
      background: linear-gradient(180deg, rgba(122,178,255,0.65), rgba(184,155,255,0.2));
    }}
    .timeline-item {{
      position: relative;
      padding-left: 34px;
    }}
    .timeline-item::before {{
      content: "";
      position: absolute;
      left: 6px;
      top: 8px;
      width: 14px;
      height: 14px;
      border-radius: 50%;
      background: linear-gradient(180deg, #7ab2ff, #b89bff);
    }}
    .timeline-item h3 {{ margin: 0 0 6px; font-size: 15px; color: {theme["text"]}; }}
    .quote {{
      border-left: 3px solid {theme["quote_line"]};
      background: {theme["quote_bg"]};
      border-radius: 0 14px 14px 0;
      padding: 13px 14px;
      color: {theme["text"]};
      margin-top: 10px;
      font-size: 14px;
    }}
    .callout {{
      margin-top: 10px;
      border: 1px solid {theme["line"]};
      border-radius: 16px;
      padding: 14px;
      background: rgba(255,255,255,0.03);
    }}
    .callout.tone-good {{ background: rgba(117,224,167,0.08); border-color: rgba(117,224,167,0.22); }}
    .callout.tone-warn {{ background: rgba(255,190,122,0.08); border-color: rgba(255,190,122,0.22); }}
    .callout.tone-danger {{ background: rgba(255,147,204,0.08); border-color: rgba(255,147,204,0.22); }}
    .callout-title {{
      color: {theme["text"]};
      font-weight: 700;
      margin-bottom: 6px;
      font-size: 14px;
    }}
    .callout-body {{
      color: {theme["muted"]};
      font-size: 14px;
    }}
    .table-like {{
      display: grid;
      gap: 10px;
      margin-top: 8px;
    }}
    .row {{
      display: grid;
      grid-template-columns: 170px minmax(0,1fr);
      gap: 12px;
      border: 1px solid {theme["line"]};
      border-radius: 14px;
      padding: 11px 13px;
      background: rgba(255,255,255,0.02);
    }}
    .k {{ color: {theme["text"]}; font-weight: 600; font-size: 14px; }}
    .v {{ color: {theme["muted"]}; font-size: 14px; }}
    .checklist {{
      display: grid;
      gap: 10px;
      margin-top: 8px;
    }}
    .check-item {{
      border: 1px solid {theme["line"]};
      border-radius: 14px;
      background: rgba(255,255,255,0.02);
      padding: 11px 12px;
    }}
    .check-main {{
      display: flex;
      gap: 10px;
      align-items: flex-start;
    }}
    .status-badge {{
      display: inline-flex;
      white-space: nowrap;
      padding: 2px 8px;
      border-radius: 999px;
      font-size: 12px;
      font-weight: 700;
      border: 1px solid {theme["line"]};
      background: rgba(255,255,255,0.04);
      color: {theme["text"]};
      margin-top: 1px;
    }}
    .status-done, .status-completed {{
      background: rgba(117,224,167,0.12);
      border-color: rgba(117,224,167,0.28);
    }}
    .status-in_progress, .status-progress {{
      background: rgba(122,178,255,0.12);
      border-color: rgba(122,178,255,0.28);
    }}
    .status-pending {{
      background: rgba(255,190,122,0.12);
      border-color: rgba(255,190,122,0.28);
    }}
    .status-blocked {{
      background: rgba(255,147,204,0.12);
      border-color: rgba(255,147,204,0.28);
    }}
    .check-title {{
      color: {theme["text"]};
      font-size: 14px;
      font-weight: 600;
    }}
    .check-detail {{
      color: {theme["muted"]};
      font-size: 13px;
      margin-top: 3px;
    }}
    .table-wrap {{
      margin-top: 10px;
      overflow-x: auto;
      border: 1px solid {theme["line"]};
      border-radius: 14px;
    }}
    .summary-table {{
      width: 100%;
      border-collapse: collapse;
      min-width: 480px;
    }}
    .summary-table th,
    .summary-table td {{
      text-align: left;
      padding: 10px 12px;
      border-bottom: 1px solid {theme["line"]};
      vertical-align: top;
      font-size: 14px;
    }}
    .summary-table th {{
      color: {theme["text"]};
      background: rgba(255,255,255,0.04);
      font-weight: 700;
    }}
    .summary-table td {{
      color: {theme["muted"]};
    }}
    .summary-table tr:last-child td {{
      border-bottom: 0;
    }}
    .subsections {{
      display: grid;
      gap: 12px;
      margin-top: 8px;
    }}
    .subsection-card {{
      border: 1px solid {theme["line"]};
      border-radius: 16px;
      background: rgba(255,255,255,0.025);
      padding: 14px;
    }}
    .subsection-card h3 {{
      margin: 0 0 6px;
      color: {theme["text"]};
      font-size: 16px;
    }}
    .sub-lead {{
      margin: 0 0 10px;
      color: {theme["muted"]};
      font-size: 13px;
    }}
    .footer {{
      margin-top: 16px;
      color: {theme["muted"]};
      font-size: 12px;
    }}
    code {{
      background: rgba(122,178,255,0.10);
      border: 1px solid {theme["line"]};
      padding: 1px 6px;
      border-radius: 7px;
    }}
    @media (max-width: 1050px) {{
      .layout {{ grid-template-columns: 1fr; }}
      .toc {{ position: static; }}
      .meta-grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
    }}
    @media (max-width: 720px) {{
      .meta-grid {{ grid-template-columns: 1fr; }}
      h1 {{ font-size: 30px; }}
      .row {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <div class="shell">
    <section class="hero">
      <div class="eyebrow">Conversation HTML Summary</div>
      <h1>{render_text(title)}</h1>
      {f"<p>{render_text(subtitle)}</p>" if subtitle else ""}
      {meta_html}
    </section>

    <div class="layout">
      <aside class="toc">
        <h2>目录</h2>
        <a href="#tldr">TL;DR</a>
        {toc_links}
      </aside>

      <main class="content">
        <div id="tldr">{tldr_html}</div>
        {section_html}
      </main>
    </div>

    <div class="footer">
      生成时间：{esc(generated_at)} · 来源：{esc(source_name)} · 由 <code>conversation-html-summary</code> skill 渲染
    </div>
  </div>
</body>
</html>
"""


def build_default_output_path(title: str, base_dir_arg: str | None = None) -> Path:
    now = dt.datetime.now()
    date_part = now.strftime("%y%m%d")
    time_part = now.strftime("%H%M%S")
    stem = sanitize_filename_stem(title or "conversation-summary")
    filename = f"{stem}-{time_part}.html"
    base = Path(base_dir_arg) if base_dir_arg else Path(r"D:\files\AI_output")
    target_dir = base / date_part
    target_dir.mkdir(parents=True, exist_ok=True)
    return target_dir / filename


def main() -> None:
    parser = argparse.ArgumentParser(description="Render a conversation summary JSON file into HTML.")
    parser.add_argument("--input", required=True, help="Path to the summary JSON file.")
    parser.add_argument("--output", required=False, help="Path to the output HTML file.")
    parser.add_argument("--base-dir", required=False, help="Base directory for default dated output when --output is omitted.")
    parser.add_argument("--json-output", required=False, help="Optional path to also write/copy the final summary JSON.")
    parser.add_argument("--copy-input-json", action="store_true", help="Also copy the input JSON to the final output directory.")
    parser.add_argument("--theme", choices=sorted(THEMES), default="dark", help="Color theme.")
    args = parser.parse_args()

    input_path = Path(args.input)
    data = json.loads(input_path.read_text(encoding="utf-8"))
    title = data.get("title") or "Conversation Summary"
    output_path = Path(args.output) if args.output else build_default_output_path(title, args.base_dir)
    html_text = build_html(data, args.theme, input_path.name)
    output_path.write_text(html_text, encoding="utf-8")

    json_output_path: Path | None = None
    if args.json_output:
      json_output_path = Path(args.json_output)
    elif args.copy_input_json or not args.output:
      json_output_path = output_path.with_suffix(".json")

    if json_output_path is not None:
      json_output_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    print(output_path)
    if json_output_path is not None:
      print(json_output_path)


if __name__ == "__main__":
    main()
