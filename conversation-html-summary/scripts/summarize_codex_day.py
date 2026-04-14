#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import render_summary_html


PATH_PATTERN = re.compile(r"[A-Za-z]:\\[^\s<>:\"|?*\r\n]+")


def truncate_text(text: str, limit: int = 220) -> str:
    cleaned = " ".join((text or "").split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1].rstrip() + "…"


def pick_title(text: str) -> str:
    first_line = next((line.strip() for line in (text or "").splitlines() if line.strip()), "")
    if not first_line:
        return "未命名会话"
    return truncate_text(first_line, 42)


def unique_keep_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    return result


@dataclass
class SessionDigest:
    session_id: str = ""
    started_at: str = ""
    started_at_local: str = ""
    file_path: str = ""
    cwd: str = ""
    cli_version: str = ""
    originator: str = ""
    user_messages: list[str] = field(default_factory=list)
    assistant_final_answers: list[str] = field(default_factory=list)
    assistant_commentary: list[str] = field(default_factory=list)
    tool_call_count: int = 0
    command_count: int = 0
    patch_count: int = 0
    title: str = ""
    final_snippet: str = ""
    files_mentioned: list[str] = field(default_factory=list)

    def to_summary_subsection(self) -> dict[str, Any]:
        detail_rows = [
            {"key": "开始时间", "value": self.started_at_local or self.started_at},
            {"key": "工作目录", "value": self.cwd or "-"},
            {"key": "工具调用数", "value": str(self.tool_call_count)},
            {"key": "命令执行数", "value": str(self.command_count)},
            {"key": "补丁次数", "value": str(self.patch_count)},
            {"key": "原始文件", "value": self.file_path},
        ]
        blocks: list[dict[str, Any]] = [
            {"type": "kv", "items": detail_rows},
        ]
        if self.user_messages:
            blocks.append(
                {
                    "type": "bullets",
                    "items": [truncate_text(msg, 180) for msg in self.user_messages[:4]],
                }
            )
        if self.final_snippet:
            blocks.append({"type": "quote", "text": self.final_snippet})
        if self.files_mentioned:
            blocks.append(
                {
                    "type": "bullets",
                    "items": [f"提及文件：{path}" for path in self.files_mentioned[:8]],
                }
            )
        return {
            "title": self.title or "未命名会话",
            "lead": "该会话的主要用户问题、最终输出和落地产物概览。",
            "blocks": blocks,
        }


def parse_iso_to_local(timestamp: str) -> str:
    if not timestamp:
        return ""
    try:
        if timestamp.endswith("Z"):
            dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        else:
            dt = datetime.fromisoformat(timestamp)
        return dt.astimezone().strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return timestamp


def extract_paths(text: str) -> list[str]:
    return unique_keep_order(PATH_PATTERN.findall(text or ""))


def parse_session_file(path: Path) -> SessionDigest:
    digest = SessionDigest(file_path=str(path))
    files_mentioned: list[str] = []

    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            obj = json.loads(line)
            top_type = obj.get("type")
            payload = obj.get("payload") or {}

            if top_type == "session_meta":
                digest.session_id = payload.get("id", "")
                digest.started_at = payload.get("timestamp", "")
                digest.started_at_local = parse_iso_to_local(digest.started_at)
                digest.cwd = payload.get("cwd", "")
                digest.cli_version = payload.get("cli_version", "")
                digest.originator = payload.get("originator", "")
                continue

            payload_type = payload.get("type")
            if payload_type == "user_message":
                msg = (payload.get("message") or "").strip()
                if msg:
                    digest.user_messages.append(msg)
                    files_mentioned.extend(extract_paths(msg))
                continue

            if payload_type == "function_call":
                digest.tool_call_count += 1
                name = payload.get("name")
                if name == "shell_command":
                    digest.command_count += 1
                continue

            if payload_type == "patch_apply_end":
                digest.patch_count += 1
                continue

            if top_type == "response_item" and payload_type == "message" and payload.get("role") == "assistant":
                text_parts = []
                for part in payload.get("content") or []:
                    if part.get("type") in {"output_text", "input_text"}:
                        text_parts.append(part.get("text") or "")
                text = "\n".join(text_parts).strip()
                if not text:
                    continue
                phase = payload.get("phase")
                if phase == "final_answer":
                    digest.assistant_final_answers.append(text)
                else:
                    digest.assistant_commentary.append(text)
                files_mentioned.extend(extract_paths(text))

    digest.title = pick_title(digest.user_messages[0] if digest.user_messages else path.stem)
    if digest.assistant_final_answers:
        digest.final_snippet = truncate_text(digest.assistant_final_answers[-1], 240)
    elif digest.assistant_commentary:
        digest.final_snippet = truncate_text(digest.assistant_commentary[-1], 240)
    digest.files_mentioned = unique_keep_order(files_mentioned)
    return digest


def build_day_payload(date_str: str, digests: list[SessionDigest], sessions_dir: Path) -> dict[str, Any]:
    total_user_messages = sum(len(item.user_messages) for item in digests)
    total_final_answers = sum(len(item.assistant_final_answers) for item in digests)
    total_tool_calls = sum(item.tool_call_count for item in digests)
    total_commands = sum(item.command_count for item in digests)
    total_patches = sum(item.patch_count for item in digests)
    all_paths = unique_keep_order([path for item in digests for path in item.files_mentioned])

    title_counter = Counter(item.title for item in digests if item.title)
    repeated_topics = [f"{name}（{count} 次）" for name, count in title_counter.most_common(8)]

    timeline_items = [
        {
            "title": f"{item.started_at_local[-8:] if item.started_at_local else item.started_at} · {item.title}",
            "body": truncate_text(item.user_messages[0] if item.user_messages else "无可见用户消息", 180),
        }
        for item in sorted(digests, key=lambda x: x.started_at or x.file_path)
    ]

    session_subsections = [item.to_summary_subsection() for item in sorted(digests, key=lambda x: x.started_at or x.file_path)]

    payload: dict[str, Any] = {
        "title": f"Codex 全会话日报：{date_str}",
        "subtitle": f"自动汇总 {date_str} 当天全部 Codex rollout 会话",
        "meta": [
            {"label": "日期", "value": date_str},
            {"label": "会话数", "value": str(len(digests))},
            {"label": "会话目录", "value": str(sessions_dir)},
            {"label": "模式", "value": "按天汇总全部 Codex 会话"},
        ],
        "tldr": [
            f"共识别到 {len(digests)} 个会话，用户消息 {total_user_messages} 条，最终回答 {total_final_answers} 条。",
            f"累计工具调用 {total_tool_calls} 次，命令执行 {total_commands} 次，补丁修改 {total_patches} 次。",
            f"共提取到 {len(all_paths)} 个被会话提及的绝对路径，可用于回看文件产物和交接线索。",
        ],
        "sections": [
            {
                "title": "总览",
                "lead": "这是一份按天聚合的 Codex 会话总览页，优先保留用户可见任务、最终输出和产物线索。",
                "blocks": [
                    {
                        "type": "callout",
                        "title": "汇总口径",
                        "text": "默认按用户可见内容汇总，不把隐藏推理、系统提示词和底层事件噪音直接作为正文内容。",
                        "tone": "good",
                    },
                    {
                        "type": "table",
                        "columns": ["维度", "数值", "说明"],
                        "rows": [
                            ["会话数", len(digests), "当天识别到的 rollout 文件数"],
                            ["用户消息数", total_user_messages, "来自 user_message 事件"],
                            ["最终回答数", total_final_answers, "assistant final_answer 数量"],
                            ["工具调用数", total_tool_calls, "所有 function_call 总数"],
                            ["命令执行数", total_commands, "shell_command 次数"],
                            ["补丁次数", total_patches, "patch_apply_end 次数"],
                        ],
                    },
                ],
            },
            {
                "title": "高频主题",
                "lead": "按每个会话的首个用户问题粗略提取标题，便于看出当天主要关注点。",
                "blocks": [
                    {"type": "bullets", "items": repeated_topics or ["未能提取到明显的重复主题。"]},
                ],
            },
            {
                "title": "会话时间线",
                "lead": "按开始时间排列的会话索引，可快速回顾当天任务流转。",
                "blocks": [
                    {"type": "timeline", "items": timeline_items},
                ],
            },
            {
                "title": "逐会话摘要",
                "lead": "每个会话保留任务主题、关键输入、最终输出摘要和提及的文件路径。",
                "blocks": [
                    {"type": "subsections", "items": session_subsections},
                ],
            },
            {
                "title": "文件与路径线索",
                "lead": "从用户消息和助手最终回答中抽取到的绝对路径，适合继续追溯产物。",
                "blocks": [
                    {"type": "bullets", "items": all_paths[:80] or ["当天会话中未提取到明显的绝对路径。"]},
                ],
            },
            {
                "title": "后续建议",
                "lead": "如果你后面要做团队日报或项目交接，最值得继续补强的方向如下。",
                "blocks": [
                    {
                        "type": "numbered",
                        "items": [
                            "把当日所有输出文件按项目或主题再做二次聚类。",
                            "对逐会话摘要进一步做“明确内容 vs 推断”拆分。",
                            "把高频目录、反复提到的代码路径和未完事项抽成专门的交接板块。",
                        ],
                    }
                ],
            },
        ],
    }
    return payload


def list_available_dates(root: Path) -> list[str]:
    dates: list[str] = []
    if not root.exists():
        return dates
    for year_dir in root.iterdir():
        if not year_dir.is_dir() or not year_dir.name.isdigit():
            continue
        for month_dir in year_dir.iterdir():
            if not month_dir.is_dir() or not month_dir.name.isdigit():
                continue
            for day_dir in month_dir.iterdir():
                if not day_dir.is_dir() or not day_dir.name.isdigit():
                    continue
                try:
                    date_str = f"{int(year_dir.name):04d}-{int(month_dir.name):02d}-{int(day_dir.name):02d}"
                    datetime.strptime(date_str, "%Y-%m-%d")
                    dates.append(date_str)
                except Exception:
                    continue
    return sorted(dates)


def date_exists(root: Path, date_str: str) -> bool:
    parsed = datetime.strptime(date_str, "%Y-%m-%d")
    return (root / parsed.strftime("%Y") / parsed.strftime("%m") / parsed.strftime("%d")).exists()


def normalize_date_selector(selector: str | None, root: Path) -> str:
    today = datetime.now().date()
    raw = (selector or "").strip()
    token = raw.lower()

    if not raw:
        today_str = today.strftime("%Y-%m-%d")
        if date_exists(root, today_str):
            return today_str
        available = list_available_dates(root)
        if not available:
            raise FileNotFoundError(f"No dated session directories found under: {root}")
        return available[-1]
    if token in {"today", "今日", "今天", "tod"}:
        return today.strftime("%Y-%m-%d")
    if token in {"yesterday", "昨日", "昨天"}:
        return (today - timedelta(days=1)).strftime("%Y-%m-%d")
    if token in {"latest", "latest-available", "recent", "最新", "最近"}:
        available = list_available_dates(root)
        if not available:
            raise FileNotFoundError(f"No dated session directories found under: {root}")
        return available[-1]

    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y%m%d"):
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue

    raise ValueError(
        f"Unsupported date selector: {raw}. Use YYYY-MM-DD, YYYY/MM/DD, YYYYMMDD, today/今天, yesterday/昨天, or latest/最新."
    )


def resolve_sessions_dir(root: Path, date_str: str) -> Path:
    parsed = datetime.strptime(date_str, "%Y-%m-%d")
    target = root / parsed.strftime("%Y") / parsed.strftime("%m") / parsed.strftime("%d")
    if not target.exists():
        available = list_available_dates(root)
        latest_hint = f" Latest available date: {available[-1]}" if available else ""
        raise FileNotFoundError(f"Session directory not found: {target}.{latest_hint}")
    return target


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize all Codex sessions for a given day and render HTML.")
    parser.add_argument("--date", required=False, help="Date selector: YYYY-MM-DD, YYYY/MM/DD, YYYYMMDD, today/今天, yesterday/昨天, latest/最新. Defaults to today.")
    parser.add_argument("--sessions-root", default=r"C:\Users\yucohu\.codex\sessions", help="Root directory of Codex sessions.")
    parser.add_argument("--output-dir", default=r"D:\files\AI_output", help="Base output directory for dated results.")
    parser.add_argument("--list-dates", action="store_true", help="List all available session dates and exit.")
    parser.add_argument("--open", action="store_true", help="Open the generated HTML with the system default app.")
    parser.add_argument("--theme", choices=sorted(render_summary_html.THEMES), default="dark", help="HTML theme.")
    args = parser.parse_args()

    sessions_root = Path(args.sessions_root)
    if args.list_dates:
        for item in list_available_dates(sessions_root):
            print(item)
        return

    resolved_date = normalize_date_selector(args.date, sessions_root)
    sessions_dir = resolve_sessions_dir(sessions_root, resolved_date)
    session_files = sorted(sessions_dir.glob("rollout-*.jsonl"))
    if not session_files:
        raise FileNotFoundError(f"No rollout files found under: {sessions_dir}")

    digests = [parse_session_file(path) for path in session_files]
    payload = build_day_payload(resolved_date, digests, sessions_dir)

    title = payload.get("title") or f"codex-day-summary-{resolved_date}"
    html_path = render_summary_html.build_default_output_path(title, args.output_dir)
    json_path = html_path.with_suffix(".json")
    html_text = render_summary_html.build_html(payload, args.theme, str(sessions_dir))

    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    html_path.write_text(html_text, encoding="utf-8")

    print(html_path)
    print(json_path)
    if args.open:
        render_summary_html.open_output_file(html_path)


if __name__ == "__main__":
    main()
