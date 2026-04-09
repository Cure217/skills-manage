# skills-manage

一个用于管理本地 Codex / Codex CLI `skills` 目录的仓库，适合做版本备份、跨设备同步，以及持续维护自定义 Skill。

## 项目简介

这个仓库主要用于集中管理 `~/.codex/skills` 下的内容，包括：

- 系统内置 Skill 的本地副本
- 自定义 Skill 的说明、脚本和参考资料
- 便于版本管理、迁移和团队共享的目录结构

如果你正在维护自己的 Codex Skill 集合，这个仓库可以作为统一入口。

## 仓库结构

```text
skills-manage/
├─ .system/
├─ conversation-html-summary/
├─ daily-ai-news/
├─ optimize-prompt/
├─ summarize-current-conversation/
└─ README.md
```

### `.system/`

保存当前环境中的系统 Skill 副本，适合做查看、备份和版本管理。

当前包含的模块例如：

- `imagegen`
- `openai-docs`
- `plugin-creator`
- `skill-creator`
- `skill-installer`

### 自定义 Skill

当前仓库中的自定义 Skill 包括：

| Skill | 说明 |
| --- | --- |
| `conversation-html-summary` | 把对话整理成结构化 HTML 总结页 |
| `daily-ai-news` | 汇总指定日期范围内的 AI 资讯并生成中文日报 |
| `optimize-prompt` | 优化、改写和增强 Prompt |
| `summarize-current-conversation` | 总结当前会话并生成 recap / handoff 内容 |

## 示例用法

下面这些示例可以作为在 Codex / Codex CLI 中触发对应 Skill 的自然语言参考。

### 自定义 Skill 示例

#### `conversation-html-summary`

适合把一段长对话整理成可以分享或交接的 HTML 页面。

示例：

```text
帮我把当前这段对话整理成一个 HTML 总结页，包含目标、决策、已完成事项、关键文件和下一步。
```

#### `daily-ai-news`

适合汇总指定日期或时间范围内的 AI 资讯，并输出中文结构化日报。

示例：

```text
帮我汇总今天的 AI 新闻，按官方公告、开源动态、行业讨论分别整理，输出中文日报。
```

#### `optimize-prompt`

适合把原始 Prompt 优化成更清晰、更适合执行的版本。

示例：

```text
帮我把这段 Prompt 优化成适合 Codex CLI 执行的版本，保留原意并补充约束和输出格式：<你的原始 Prompt>
```

#### `summarize-current-conversation`

适合快速总结当前会话，生成 recap、状态更新或 handoff。

示例：

```text
总结一下当前对话，给我一个可以直接交接给下一个人的 handoff 版本。
```

### 系统 Skill 示例

#### `imagegen`

适合生成新图片，或基于已有图片做编辑、扩图、变体。

示例：

```text
帮我生成一张极简风格的机器人头像，白色背景，正方形，用作产品原型占位图。
```

#### `openai-docs`

适合查询 OpenAI 官方文档、模型选择建议和最新 API 用法。

示例：

```text
帮我查一下 OpenAI 最新的 Responses API 用法，并给我一个最小可运行示例和官方文档链接。
```

#### `plugin-creator`

适合创建 Codex 插件骨架和基础目录结构。

示例：

```text
帮我创建一个新的 Codex 插件骨架，插件名叫 my-local-tool，包含基础的 plugin.json。
```

#### `skill-creator`

适合新建一个自定义 Skill，或整理现有流程并沉淀成 Skill。

示例：

```text
帮我创建一个新的 Skill，用来把日报需求自动整理成统一模板，并生成初始目录结构。
```

#### `skill-installer`

适合从已有来源安装或引入 Skill 到本地 `skills` 目录。

示例：

```text
帮我安装一个用于 Prompt 优化的 Codex Skill，放到当前本地 skills 目录里。
```

## Skill 目录约定

一个 Skill 目录通常包含以下内容：

- `SKILL.md`：Skill 的核心说明和触发规则
- `agents/`：相关 Agent 配置
- `references/`：参考文档、模板或补充说明
- `scripts/`：辅助脚本
- `assets/`：图片或展示资源（按需存在）

这样的结构方便维护、迁移和复用。

## 快速开始

### 方式一：直接克隆到本地 Skill 目录

```bash
git clone https://github.com/Cure217/skills-manage.git ~/.codex/skills
```

Windows 环境通常对应：

```powershell
git clone https://github.com/Cure217/skills-manage.git $env:USERPROFILE\.codex\skills
```

### 方式二：已有本地仓库时更新

```bash
git pull origin master
```

## 适用场景

- 维护自己的 Codex Skill 集合
- 在多台电脑之间同步 Skill
- 把常用 Prompt / 工作流沉淀成可复用 Skill
- 为后续新增 Skill 提供统一仓库结构

## 维护建议

- 优先把可复用规则写进 `SKILL.md`
- 脚本、模板、参考资料尽量和对应 Skill 放在同一目录
- 提交前检查缓存文件、临时文件和敏感信息
- 不要提交真实的 API Key、Token、密码、私钥等内容

当前仓库已通过 `.gitignore` 忽略常见 Python 缓存，例如：

- `__pycache__/`
- `*.pyc`

## 后续可扩展方向

后续可以继续补充：

- 每个 Skill 的示例用法
- 统一的开发规范
- 更新日志
- 安装与迁移指南
- 自定义 Skill 模板

如果 Skill 数量继续增加，建议再补一个统一索引章节，集中列出每个 Skill 的用途、适用场景和入口说明。
