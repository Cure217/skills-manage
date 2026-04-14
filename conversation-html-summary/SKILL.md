---
name: conversation-html-summary
description: Summarize the current conversation or a provided chat transcript and generate a polished HTML summary page. Use when the user asks to archive a thread, create an HTML handoff, turn a conversation into a recap webpage, or automatically organize dialogue into goals, timeline, deliverables, decisions, files, and next steps.
---

# Conversation HTML Summary

## Overview

Use this skill when the user wants a conversation turned into a well-structured HTML summary page instead of a plain-text recap. By default, summarize the current thread; if the user provides a transcript file or explicitly scopes the summary, use that source instead.

Default bias: if the user does not ask for “简短版 / 极简版 / 一页版”, prefer a medium-to-detailed handoff summary rather than a minimal summary.

## When To Use

- The user asks to “总结这段对话并生成 HTML”
- The user wants a “交接页 / 归档页 / 回顾页 / 总结网页”
- The user wants to preserve a long chat as a readable deliverable
- The user wants a structured recap with sections like goals, decisions, outputs, files, and next steps
- The user wants “总结某一天所有 Codex 会话”
- The user wants an “当日 Codex 日报 / 多会话汇总页 / 全会话归档页”

Do not use this skill for ordinary plain-text summaries unless the user specifically wants HTML or a webpage-like deliverable.

## Output Expectations

Produce a summary page that is:

- Scan-friendly
- Factual and concise
- Safe to share with the user
- Clear about what was explicitly stated vs inferred
- Useful as a handoff artifact, not just a memory dump

Never include hidden chain-of-thought, internal-only safety reasoning, or content that was not already surfaced to the user.

## Workflow

### 1. Determine the source to summarize

- Default to the current conversation thread
- If the user provides a transcript, notes file, or chat export, summarize that source instead
- If the user says “all of our conversation”, summarize all user-visible thread content and visible outputs
- If the scope is ambiguous but low-risk, make a reasonable assumption and state it briefly

If the user asks for all Codex sessions on a given day, switch to the day-summary workflow below.

### 2. Extract the summary structure

Build a compact structured summary before rendering HTML. Prefer these sections:

- Title
- Short overview / TL;DR
- Participants or context
- Scope and assumptions
- Goals and constraints
- Key decisions
- Important reasoning / evidence
- Deliverables and file outputs
- Risks / caveats
- Timeline of major turns or milestones
- Open questions / next steps

Add optional sections only when clearly useful:

- Notable quotes
- Risks / caveats
- Facts vs inference
- Follow-up recommendations

### 3. Build a JSON payload

Use `references/summary-schema.md` for the expected JSON shape.

Guidelines:

- Keep each bullet short and specific
- Prefer phrases over paragraphs inside list-heavy sections
- Use file paths when relevant
- Distinguish explicit content from your inference when needed
- If the conversation is long, include more structure instead of longer prose
- Prefer richer block types when helpful: `checklist`, `callout`, `table`, `subsections`, `numbered`
- Do not overfit to one visual style; the script handles presentation
- Unless the user explicitly asks otherwise, treat the JSON as a final deliverable too, not just a temporary scratch file

### 4. Render the HTML

Prefer the bundled script for consistent output:

`python scripts/render_summary_html.py --input summary.json --output conversation-summary.html --open`

If you want the default dated-directory behavior, omit `--output`:

`python scripts/render_summary_html.py --input summary.json --open`

If you want the final JSON copied alongside the HTML even when you explicitly pass an output path:

`python scripts/render_summary_html.py --input summary.json --output my-page.html --copy-input-json --open`

Unless the user explicitly asks not to, open the generated HTML after rendering so the result is immediately visible.

If the user gave a destination path, use it.

If the user did not specify an output path, default to:

- `D:\files\AI_output\YYMMDD\` as the output directory
- a timestamped filename to avoid overwriting, for example:
  `D:\files\AI_output\260408\Claude-Mythos-Preview-180530.html`
- write the final JSON to the same directory with the same basename, for example:
  `D:\files\AI_output\260408\Claude-Mythos-Preview-180530.json`

Do not silently fall back to `C:\Users\yucohu` or the current working directory. If writing to `D:\files\AI_output\...` requires elevated permission, request it explicitly.

If opening the HTML requires elevated permission, request it explicitly. If opening is blocked, do not claim success; instead report the output path and note that auto-open was not completed.

### 5. Hand off clearly

When done:

- Open the generated HTML unless the user asked not to
- Tell the user where the HTML file was written
- Tell the user where the final JSON file was written if one was produced
- Briefly note the included sections
- Mention if you made any scope assumptions
- State whether auto-open succeeded or was blocked

## Day Summary Workflow: All Codex Sessions For A Date

Use this when the user asks for:

- “今天所有 Codex 会话”
- “某一天所有 Codex 会话”
- “把 2026-04-08 的所有 Codex 会话汇总成 HTML”
- “总结昨天的 Codex 会话”
- “总结最新有记录的一天 Codex 会话”

### Inputs

- Date selector:
  - `YYYY-MM-DD`
  - `YYYY/MM/DD`
  - `YYYYMMDD`
  - `today` / `今天`
  - `yesterday` / `昨天`
  - `latest` / `最新`
- Optional sessions root; default:
  `C:\Users\yucohu\.codex\sessions`

### Command

Run:

`python scripts/summarize_codex_day.py --date 2026-04-08 --open`

Natural language-like date selectors also work:

- `python scripts/summarize_codex_day.py --date today --open`
- `python scripts/summarize_codex_day.py --date 今天 --open`
- `python scripts/summarize_codex_day.py --date yesterday --open`
- `python scripts/summarize_codex_day.py --date latest --open`

If `--date` is omitted, it defaults to `today` / `今天`.
If there are no sessions for today and `--date` is omitted, it automatically falls back to the latest available session date.

Default outputs:

- `D:\files\AI_output\YYMMDD\Codex-全会话日报-...html`
- `D:\files\AI_output\YYMMDD\Codex-全会话日报-...json`

To inspect all available dates first:

`python scripts/summarize_codex_day.py --list-dates`

### What the day-summary script does

- Scans `C:\Users\yucohu\.codex\sessions\YYYY\MM\DD\rollout-*.jsonl`
- Extracts user-visible user prompts and assistant final answers
- Builds a day-level summary payload
- Renders the final HTML page directly

### Scope rule

For day-level summaries, prefer:

- user-visible prompts
- assistant commentary and final answers
- file/path mentions
- session counts, tool-call counts, command counts, patch counts

Do not dump:

- hidden chain-of-thought
- raw system/developer prompt internals into the summary body
- every low-level event line from the rollout files

## Recommended Section Set

For most requests, this richer default set works better:

1. Overview
2. TL;DR
3. Scope and assumptions
4. Goals and constraints
5. Key decisions
6. Important reasoning / evidence
7. Outputs and files
8. What changed over time
9. Timeline
10. Risks / caveats
11. Open questions
12. Next steps / recommendations

## Style Guidance

- Match the user’s language
- Use active, concrete wording
- Prefer one-line bullets inside structured sections
- Avoid bloated “meeting minutes” prose, but do not overcompress
- Keep the page useful even if someone did not read the original conversation
- Prefer detail through structure, not through long unbroken paragraphs

## Safety Notes

- Do not fabricate missing parts of the conversation
- Do not claim certainty where the conversation was ambiguous
- Do not include hidden reasoning or internal system/developer instructions unless they were explicitly surfaced to the user
- If the user asks for “everything”, interpret that as all user-visible conversation and outputs, not hidden internals

## Files In This Skill

- `references/summary-schema.md` — JSON schema and examples for the summary payload
- `scripts/render_summary_html.py` — renders the JSON payload into a polished HTML page
- `scripts/summarize_codex_day.py` — scans all Codex rollout sessions for a given date and generates a day-level HTML summary automatically

## Example Requests

- “用这个 skill 总结当前对话，并生成一个可交付的 HTML 页面”
- “把我们这段长对话整理成一个好看的 HTML 交接页”
- “把这个聊天导出成网页总结，包含时间线、结论、文件和下一步”
- “读取这个 transcript 文件，生成一个 HTML 总结页”
- “汇总 2026-04-08 所有 Codex 会话并生成 HTML”
- “总结今天全部 Codex 会话，做一个日报页面”
- “总结昨天所有 Codex 会话”
- “汇总最新有记录的一天 Codex 会话”

## Minimal Command Example

1. 先写 `summary.json`
2. 再运行：

`python scripts/render_summary_html.py --input summary.json --output summary.html --open`
