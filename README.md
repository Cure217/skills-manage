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
