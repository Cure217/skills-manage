---
name: harness-engineering
description: Design or apply Harness Engineering workflows for Codex CLI, Claude Code, coding agents, long-running agent tasks, .harness task state, AGENTS.md, CLAUDE.md, verification loops, context engineering, agent task packets, multi-agent coordination, and review/validation systems. Use when the user asks to build, adapt, explain, initialize, or improve a coding-agent harness.
---

# Harness Engineering

## 目标

- 帮用户把编码 Agent 的工作从“单次 prompt”升级为“上下文、任务、进度、验证、审查”的闭环系统。
- 默认适配 `Codex CLI` 与 `Claude Code`。
- 输出应可直接落地到仓库，而不是只讲抽象概念。

## 核心原则

- 不依赖模型记忆续跑任务，优先依赖仓库内工件。
- 不让 Agent 主观定义完成，优先依赖验收标准、测试、构建、smoke 与人工审查。
- 不把上下文堆满，优先分层、按需、可作用域化地提供上下文。
- 不急着多 Agent 并行，先拆清任务、写集和验证边界。
- 不把架构写成口号，尽量转成可执行检查或明确审查标准。

## 默认结构

建议在目标仓库中使用：

```text
repo/
├─ AGENTS.md
├─ CLAUDE.md
├─ docs/
│  ├─ product.md
│  ├─ architecture.md
│  ├─ commands.md
│  └─ test-strategy.md
├─ .harness/
│  ├─ progress.md
│  ├─ feature-list.json
│  ├─ decisions.md
│  ├─ unknowns.md
│  └─ task-packets/
│     └─ TASK-001.md
└─ scripts/
   ├─ verify.ps1
   ├─ smoke.ps1
   └─ architecture-check.ps1
```

如果用户只要求最小可用版本，优先创建：

- `AGENTS.md`
- `CLAUDE.md`
- `.harness/progress.md`
- `.harness/feature-list.json`
- `.harness/task-packets/TASK-001.md`
- `scripts/verify.ps1`

## 本机模板

默认模板目录：

```text
C:\Users\yucohu\.harness-template\
```

其中包含：

- `progress.md`
- `feature-list.json`
- `TASK-001.md`

使用方式：

- 将 `progress.md` 复制到目标仓库的 `.harness/progress.md`
- 将 `feature-list.json` 复制到目标仓库的 `.harness/feature-list.json`
- 将 `TASK-001.md` 复制到目标仓库的 `.harness/task-packets/TASK-001.md`

复制前应根据真实任务替换占位内容，不要把模板当成最终任务事实。

## Codex CLI 适配

给 `Codex CLI` 的 harness 应更短、更硬、更执行导向：

- 明确写集
- 明确禁止无关重构
- 明确验证命令
- 明确最终汇报格式
- 每轮只推进一个最小闭环

适合 Codex 的任务提示词：

```text
请按当前任务包执行修改。

要求：
1. 先读 `AGENTS.md`
2. 再读 `.harness/task-packets/TASK-xxx.md`
3. 再读 `.harness/progress.md`
4. 只处理当前一个任务项
5. 只做最小必要修改
6. 完成后运行 `scripts/verify.ps1`
7. 更新 `.harness/progress.md` 和 `.harness/feature-list.json`

输出必须包含：
- 修改文件
- 根因
- 修复方式
- 验证结果
- 剩余风险
```

## Claude Code 适配

给 `Claude Code` 的 harness 应更适合长链路承接：

- 默认按 `Research / Plan / Implement / Verify` 推进
- 长任务必须外部化进度、未知项和关键决策
- 每轮只推进一个最小闭环
- 续跑时先读 `.harness/progress.md`、`.harness/decisions.md` 和当前任务包

适合 Claude Code 的续跑提示词：

```text
请作为续跑 agent 接手当前任务。

先做：
1. 阅读 `CLAUDE.md`
2. 阅读 `.harness/progress.md`
3. 阅读 `.harness/decisions.md`
4. 阅读当前任务包
5. 总结：
   - 当前已经完成什么
   - 当前卡在哪里
   - 下一步最小动作是什么

然后只推进一个最小闭环，不要试图一轮做完整个大任务。
```

## 输出要求

根据用户场景输出以下一种：

- **设计方案**：说明目录、文件职责、执行流程、验证回路。
- **初始化清单**：列出应创建的文件和推荐内容。
- **可复制文件内容**：直接给出 `AGENTS.md`、`CLAUDE.md`、`.harness` 模板。
- **改造建议**：基于现有仓库指出上下文、验证、任务拆解、审查回路的缺口。

默认使用简体中文，结论先行，避免空泛方法论。
