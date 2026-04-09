# Conversation Summary JSON Schema

Use this schema when preparing data for `scripts/render_summary_html.py`.

## Minimal shape

```json
{
  "title": "对话总结标题",
  "subtitle": "可选副标题",
  "meta": [
    { "label": "主题", "value": "Claude Mythos Preview" },
    { "label": "范围", "value": "当前对话" }
  ],
  "tldr": [
    "一句话结论 1",
    "一句话结论 2"
  ],
  "sections": [
    {
      "title": "核心结论",
      "lead": "可选导语",
      "blocks": [
        {
          "type": "bullets",
          "items": [
            "要点 1",
            "要点 2"
          ]
        }
      ]
    }
  ]
}
```

## Supported block types

### `paragraph`

```json
{ "type": "paragraph", "text": "一段简短正文。" }
```

### `bullets`

```json
{
  "type": "bullets",
  "items": ["条目 1", "条目 2", "条目 3"]
}
```

### `numbered`

```json
{
  "type": "numbered",
  "items": ["步骤 1", "步骤 2", "步骤 3"]
}
```

### `timeline`

```json
{
  "type": "timeline",
  "items": [
    { "title": "阶段 1", "body": "发生了什么" },
    { "title": "阶段 2", "body": "发生了什么" }
  ]
}
```

### `cards`

```json
{
  "type": "cards",
  "items": [
    { "title": "结论", "body": "正文", "tone": "good" },
    { "title": "风险", "body": "正文", "tone": "warn" },
    { "title": "问题", "body": "正文", "tone": "danger" }
  ]
}
```

Available tones:

- `default`
- `good`
- `warn`
- `danger`

### `quote`

```json
{
  "type": "quote",
  "text": "一句值得突出展示的话。"
}
```

### `checklist`

```json
{
  "type": "checklist",
  "items": [
    { "title": "完成阅读笔记", "detail": "已输出中文高质量摘要", "status": "done" },
    { "title": "完善 skill", "detail": "补充更详细 schema 与 HTML 渲染能力", "status": "in_progress" },
    { "title": "继续验证", "detail": "补跑详细版示例", "status": "pending" }
  ]
}
```

Available statuses:

- `done` / `completed`
- `in_progress`
- `pending`
- `blocked`

### `callout`

```json
{
  "type": "callout",
  "title": "注意",
  "text": "这里写需要特别强调的提醒。",
  "tone": "warn"
}
```

### `table`

```json
{
  "type": "table",
  "columns": ["维度", "结论", "备注"],
  "rows": [
    ["能力", "明显提升", "尤其是代理与网络安全"],
    ["风险", "仍需谨慎", "边缘案例后果更大"]
  ]
}
```

### `subsections`

```json
{
  "type": "subsections",
  "items": [
    {
      "title": "显式内容",
      "lead": "文中明确说到的内容",
      "blocks": [
        { "type": "bullets", "items": ["结论 1", "结论 2"] }
      ]
    },
    {
      "title": "推断",
      "blocks": [
        { "type": "bullets", "items": ["推断 1", "推断 2"] }
      ]
    }
  ]
}
```

### `kv`

```json
{
  "type": "kv",
  "items": [
    { "key": "输出文件", "value": "D:\\\\files\\\\AI_output\\\\260408\\\\mythos_training_flow.html" },
    { "key": "结论", "value": "需要做纯离线版" }
  ]
}
```

## Recommended default section set

For a high-quality handoff-style conversation summary, prefer this richer default set:

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

## Practical guidance

- Unless the user explicitly asks for a short recap, bias toward a medium-to-detailed summary rather than a minimal summary
- Keep `tldr` at 3-6 bullets
- Use multiple sections when the conversation contains several deliverables, revisions, or decisions
- Prefer `timeline` for multi-step work, `cards` for comparisons, `table` for compact cross-dimension summaries, and `subsections` for “明确内容 vs 推断” kinds of splits
- Use `kv` for files, paths, status, deliverable metadata, and output locations
- Use `checklist` when the conversation included iterative work or TODO-like progress
- Keep large raw transcripts out of the HTML unless the user explicitly asks for them

## Suggested detailed section prompts

When the conversation is long or multi-stage, these prompts usually yield a better page:

- 这段对话的目标经历了哪些变化？
- 有哪些明确结论，哪些只是推断？
- 过程中产出了哪些文件、页面、脚本或目录？
- 哪些地方已经完成，哪些仍未完成？
- 最值得后续继续追问的问题是什么？

## Example richer payload

```json
{
  "title": "Claude Mythos Preview 对话总结",
  "subtitle": "阅读笔记、训练拆解与 HTML 产出",
  "meta": [
    { "label": "主题", "value": "Claude Mythos Preview System Card" },
    { "label": "范围", "value": "本轮完整对话" },
    { "label": "产物", "value": "阅读总结页、训练流程图 HTML" }
  ],
  "tldr": [
    "完成了 PDF 阅读并产出中文高质量笔记。",
    "讨论了 AI 距离“有思想”还有多远，并做了三层区分。",
    "解释了 Mythos 的训练框架，并做成了 HTML 流程图页。"
  ],
  "sections": [
    {
      "title": "关键结论",
      "lead": "这是整段对话最重要的结论整理。",
      "blocks": [
        {
          "type": "cards",
          "items": [
            { "title": "文档核心", "body": "能力最强，但不公开发布。", "tone": "warn" },
            { "title": "训练框架", "body": "预训练 + 大量后训练/RL + 持续评估修正。", "tone": "good" },
            { "title": "前沿判断", "body": "AI 已经开始像在思考，但距离证明主观意识还远。", "tone": "default" }
          ]
        }
      ]
    },
    {
      "title": "产出文件",
      "blocks": [
        {
          "type": "kv",
          "items": [
            { "key": "HTML 页面", "value": "D:\\\\files\\\\AI_output\\\\260408\\\\mythos_training_flow.html" }
          ]
        }
      ]
    }
  ]
}
```
