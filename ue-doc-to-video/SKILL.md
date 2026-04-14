---
name: ue-doc-to-video
description: Turn documentation, feature specs, tutorials, PRDs, or notes into Unreal Engine teaching video packages. Use when Codex needs to convert docs into UE tutorial outlines, chapter plans, shot lists, voiceover scripts, subtitle drafts, Sequencer capture plans, Movie Render Queue checklists, or render-ready teaching video assets.
---

# UE Doc to Video

## 目标

- 把“文档/说明/设计稿/笔记”转换成**可执行的 UE 教学视频制作包**。
- 默认服务对象是：
  - `Codex CLI`
  - `Claude Code`
  - 需要把技术文档讲成“教程视频”的内容生产流程
- 输出不是一句泛泛建议，而是一套可落地交付物。

## 适用场景

当用户提出以下需求时使用本 Skill：

- “根据文档生成 UE 教学视频”
- “把 Unreal Engine 教程文档做成视频脚本”
- “给我做 UE 教学视频分镜 / 讲稿 / 字幕”
- “根据功能文档做虚幻引擎演示视频”
- “把说明文档改成适合 B 站新手教程的视频结构”

## 默认交付物

除非用户明确要求只要其中一部分，否则默认输出以下文件或等价结构：

1. `video-plan.md`
   - 课程定位
   - 目标受众
   - 视频长度建议
   - 章节结构
   - 每章学习目标
2. `voiceover.md`
   - 配音讲稿
   - 屏幕动作提示
   - 术语解释
3. `shot-list.csv`
   - 镜头编号
   - 章节
   - 画面内容
   - UE 操作步骤
   - 录屏方式
   - 是否需要字幕/标注/B-roll
4. `subtitle.srt`
   - 初版字幕草稿
5. `asset-checklist.md`
   - 需要准备的项目文件、素材、插件、字体、图标、封面文案
6. `production-notes.md`
   - 录制顺序
   - Sequencer / Movie Render Queue / 录屏方案
   - 常见风险与补录点

## 推荐风格

默认采用“B 站新手友好教程”结构，而不是学术演讲结构：

- 先给效果预览
- 再说环境准备
- 再拆步骤
- 每段只讲一个明确目标
- 关键操作要给“预期结果”
- 常见坑单独提醒
- 收尾给总结和下一步建议

如果用户特别提到某位 UP 主风格，例如“小白debug”，可以**参考其“新手友好、步骤明确、结果导向”的常见教程节奏**；  
如果没有稳定来源可验证其特定结构，不要声称完全复刻，只做风格借鉴。

## 工作流

### 1. 先判断输入材料类型

识别当前输入属于哪一类：

- 产品/需求文档
- 技术实现文档
- 功能设计说明
- 使用手册
- PRD / 方案文档
- 零散笔记 / 会议纪要

如果输入不完整，先输出“缺口清单”，但不要因此停止；至少先生成一版可用的视频结构草稿。

### 2. 判断输出深度

默认按以下四档选择，未指定时使用第 3 档：

1. **Outline only**
   - 只产出视频大纲
2. **Script package**
   - 产出大纲 + 讲稿 + 分镜
3. **Production package**
   - 产出大纲 + 讲稿 + 分镜 + 字幕草稿 + 资产清单 + 录制说明
4. **Render-ready assist**
   - 在第 3 档基础上，继续补充 Sequencer / Movie Render Queue / TTS / 字幕合成建议

### 3. 判断视频类型

把教程视频分成以下类型之一：

- `Feature walkthrough`：功能讲解
- `Step-by-step build`：一步步搭建
- `Debug / troubleshooting`：排错教学
- `Architecture / concept`：概念解释
- `Comparison / migration`：版本、方案对比

不同类型的视频要调整结构：

- `Feature walkthrough` 更重“结果预览 + 功能入口 + 演示”
- `Step-by-step build` 更重“顺序 + 操作 + 中间结果”
- `Debug / troubleshooting` 更重“错误现象 + 定位 + 修复 + 验证”

### 4. 生成教学结构

优先把文档拆成：

- 视频标题
- 受众画像
- 前置知识
- 章节
- 每章 1 个核心目标
- 每章 1 个可见结果
- 每章 1～3 个常见问题

默认视频结构建议：

1. 开场 10～20 秒：结果预览 + 你将学到什么
2. 环境准备：引擎版本、插件、项目文件、素材
3. 主体章节：每章一个清晰目标
4. 常见坑 / Debug
5. 总结 + 下一步

### 5. 转成镜头和讲稿

每章都要拆成：

- 旁白
- 屏幕动作
- 关键 UI 元素
- 是否需要放大/高亮
- 是否需要对比图
- 是否需要插入结果镜头

镜头设计优先级：

1. **真实 UE 操作画面**
2. **Sequencer 预录镜头**
3. **静态示意图 / 配图**
4. **补充字幕 / 提示条**

### 6. 选择制作方案

根据用户环境判断：

- 如果有真实 UE 项目和可运行环境：
  - 优先用 UE 内录 / 录屏 / Sequencer / Movie Render Queue
- 如果只有文档没有项目：
  - 优先输出“脚本包 + 分镜 + 资产清单”
- 如果用户要 AI 配音：
  - 优先输出可给 TTS 的 `voiceover.md`
- 如果用户要自动化字幕：
  - 生成 `subtitle.srt` 草稿

## Unreal Engine 录制建议

默认优先使用以下思路：

- UI/编辑器操作教学：
  - 屏幕录制
  - 必要时结合鼠标高亮与按键提示
- 场景演示 / 动画 / 镜头运动：
  - `Sequencer`
  - `Movie Render Queue`

如果用户要求“高质量成片”，默认提醒：

- 编辑器操作录屏和 Sequencer 渲染是两套素材源
- 最终成片通常需要后期拼接
- 不要假设所有镜头都应该从编辑器实时录制

## 常用外部工具栈建议

本 Skill 不强绑定单一厂商，但可优先建议以下组合：

- **配音**
  - ElevenLabs TTS
  - 人声实录
- **字幕**
  - 先生成 `subtitle.srt`
  - 再用剪辑工具或 `ffmpeg` 烧录
- **片头 / 图文动画 / 结构化排版**
  - Remotion
  - 剪映 / Premiere / CapCut / Resolve
- **转写校对**
  - Whisper / Speech-to-Text

如果环境里已安装相关 skill，例如 `speech-to-text`，可以配合使用做字幕回校。

## 输出要求

默认输出顺序：

1. `CR-style` 结论先行：
   - 这个文档适不适合做视频
   - 推荐视频类型
   - 推荐长度
   - 主要风险
2. 再输出交付包：
   - 标题
   - 章节
   - 讲稿
   - 分镜
   - 资产清单
   - 录制建议

## 不要做的事

- 不要假装已经渲染出真实视频，除非用户提供了项目和渲染链路并实际完成
- 不要把“脚本包”说成“成片”
- 不要在没有项目文件时杜撰 UE 场景细节
- 不要把不确定的镜头动作写成已验证事实
- 不要把所有内容都塞进一条长讲稿；优先章节化、镜头化

## 何时读取额外模板

如果要生成可直接交付的内容，请同时查看：

- `assets/video-plan-template.md`
- `assets/voiceover-template.md`
- `assets/shot-list-template.csv`
- `assets/subtitle-template.srt`
- `references/pipeline.md`

## 最小落地建议

如果用户只给了一篇文档，默认最小输出为：

- 视频标题
- 章节结构
- 3 分钟版讲稿
- 关键镜头清单
- 所需素材列表

如果用户给了文档 + UE 项目路径，默认升级输出为：

- 录制顺序
- Sequencer / 录屏分工
- Movie Render Queue 建议
- 字幕草稿
- 补录风险点
