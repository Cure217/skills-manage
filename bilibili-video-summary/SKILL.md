---
name: bilibili-video-summary
description: 提取 B站视频的公开元数据、章节点与字幕可用性，并生成中文摘要、时间轴笔记和要点总结。也支持导出公开视频字幕，或对用户提供的本地音视频做完整转写。适用于用户要快速了解某个 B站视频讲了什么、是否有公开字幕、适不适合继续看，或整理自己的本地视频字幕稿时。
---

# Bilibili Video Summary

## 何时使用

在以下场景触发本 Skill：

- 用户要看某个 `B站视频` 的摘要、总结、时间轴笔记
- 用户要判断一个 B站视频 `有没有公开字幕`
- 用户要快速了解某个视频讲了什么，而不是自己看完整个视频
- 用户要把一个视频整理成 `核心观点 / 结构提纲 / 观看建议`

## 先做什么

优先运行脚本抓取公开上下文：

```powershell
py -3 scripts/fetch_bilibili_video_context.py --url "https://www.bilibili.com/video/BV1dpQTB3EXg" --format json
```

也支持直接传 `bvid`：

```powershell
py -3 scripts/fetch_bilibili_video_context.py --bvid BV1dpQTB3EXg --format markdown
```

如果你要导出完整字幕稿：

```powershell
py -3 scripts/export_bilibili_transcript.py --url "https://www.bilibili.com/video/BV1dpQTB3EXg" --format markdown
```

如果视频没有公开字幕，但你手头有本地音视频文件：

```powershell
py -3 scripts/export_bilibili_transcript.py --url "https://www.bilibili.com/video/BV1dpQTB3EXg" --media "C:\\path\\to\\video.mp4" --backend faster_whisper --format markdown
```

## 输出工作流

### 1. 先判断公开材料够不够

脚本会返回：

- 视频标题、作者、发布时间、时长、链接
- 播放 / 点赞 / 收藏 / 分享等基础数据
- 视频简介
- 官方章节点（如果有）
- 公开字幕是否可用

### 2. 再决定摘要粒度

如果 `public_subtitles.available = true`：

- 可以基于公开字幕 + 章节点做更细的摘要
- 可以输出更完整的时间轴笔记
- 可以按需导出完整字幕稿

如果 `public_subtitles.available = false`：

- 明确说明“当前无公开字幕轨”
- 基于 `标题 + 简介 + 章节点 + 基础数据` 输出摘要
- 如果用户提供了本地音视频文件，可走本地 ASR 转写得到完整字幕稿
- 避免假装自己已经拿到了公开字幕

### 3. 推荐输出结构

优先输出：

- 一句话总结
- 主题拆解
- 时间轴 / 章节点
- 适合谁看
- 是否值得继续深看

## 输出约束

- 不要把“没有公开字幕”的视频说成“已拿到公开字幕”
- 不要虚构视频细节
- 当结论来自章节点推断时，要明确写“基于章节点 / 简介判断”
- 没有公开字幕时，如未提供本地音视频文件，不要伪造完整字幕稿

## 何时读额外文件

- 需要抓取公开上下文时：直接运行 `scripts/fetch_bilibili_video_context.py`
- 需要导出字幕稿时：运行 `scripts/export_bilibili_transcript.py`

## 扩展方式

如果后续要增强：

1. 可以继续补充更多 B站公开接口字段
2. 可以补充章节图、合集信息、相关视频等上下文
3. 如果用户提供了自己有权处理的字幕文件，再单独做本地摘要或整理

## 注意事项

- 本 Skill 支持两种字幕来源：公开视频字幕、用户提供的本地音视频转写
- 某些视频没有公开字幕，这时只能做“基于章节点和简介”的摘要，或要求用户提供本地文件
- 本地转写默认使用 `faster-whisper`，首次运行可能需要安装依赖并下载模型
- 若 B站接口在当前网络环境受限，需明确说明失败原因
