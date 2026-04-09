---
name: daily-ai-news
description: 汇总今天、昨天、指定日期、最近 N 天或日期区间的 AI 资讯，并生成中文结构化日报。适用于用户要看每日 AI 新闻、官方公告、开源动态、视频更新或行业讨论时；优先使用官方、一手、稳定来源，自动去重，并把低可信内容与抓取失败来源单独列出。
---

# Daily AI News

## 何时使用

在以下场景触发本 Skill：

- 用户要看“今天 / 昨天 / 2026-04-08 的 AI 资讯”
- 用户要生成“AI 日报 / AI 快报 / AI 资讯汇总”
- 用户要求同时覆盖官方、开源、视频、社交等来源
- 用户强调“不要伪造抓取成功”“按日期查询”“结构化输出”“单独分组低可信信息”

## 快速开始

默认时区为 `Asia/Shanghai`。优先直接运行脚本，再基于脚本结果整理中文日报。

常用命令：

```powershell
py -3 scripts/ai_news_digest.py --preset today --format markdown
py -3 scripts/ai_news_digest.py --preset yesterday --format markdown
py -3 scripts/ai_news_digest.py --date 2026-04-08 --format markdown
py -3 scripts/ai_news_digest.py --days 3 --format markdown
py -3 scripts/ai_news_digest.py --start 2026-04-01 --end 2026-04-08 --format json
```

如果要看详细抓取日志：

```powershell
py -3 scripts/ai_news_digest.py --preset today --format markdown --verbose
```

## 工作流

### 1. 先解析日期

优先把用户请求转换成以下参数之一：

- 今天：`--preset today`
- 昨天：`--preset yesterday`
- 指定日期：`--date YYYY-MM-DD`
- 最近 N 天：`--days N`
- 日期区间：`--start YYYY-MM-DD --end YYYY-MM-DD`

除非用户明确要求其他时区，否则统一使用 `--timezone Asia/Shanghai`。

### 2. 运行脚本获取结构化结果

脚本默认会：

- 加载 `references/sources.json`
- 按来源配置抓取 RSS / 页面 / GitHub API / GitHub Trending / YouTube
- 对标题和链接做去重
- 输出以下栏目：
  - 重大模型/产品发布
  - 官方公告/能力更新
  - 开源项目/代码趋势
  - 行业热点/讨论
  - 低可信/待验证信息
- 单独列出抓取失败、无结果、未启用来源

### 3. 输出时必须遵守

- 不要把抓取失败的来源写成成功
- 不要把低可信内容混入高可信栏目
- 允许某些来源当日无结果，但必须说明原因
- 允许某些来源因站点限制失败，但必须展示失败原因

## 默认来源策略

本 Skill 优先级如下：

1. 官方 API
2. RSS / Feed
3. 页面解析
4. GitHub Releases / Trending
5. 可维护的来源配置表

默认已内置的可运行来源与接入方式请看 `references/sources.md`。

默认已内置但可能受环境影响的来源：

- OpenAI News RSS
- Anthropic Newsroom 页面解析
- Google AI 页面解析
- Google DeepMind 页面解析
- Hugging Face Blog RSS
- GitHub Releases
- GitHub Trending
- YouTube 频道 Feed / Handle 解析

默认不硬编码死解释、而是保留为可配置别名的来源：

- `X(Twitter)`
- `B站`
- `V站`
- `L站`

这些来源默认会在结果里显示为“待配置 / 未启用”，除非你在 `references/sources.json` 中补充可维护的代理、RSS、API 或桥接地址。

## 输出要求

默认优先使用 `--format markdown`，输出适合人直接阅读的中文日报。

如果用户明确要二次处理或接数据库、自动化流水线，使用：

```powershell
py -3 scripts/ai_news_digest.py --date 2026-04-08 --format json
```

## 何时读额外参考

- 调整默认来源、启用别名源、补充新仓库时：读 `references/sources.json`
- 想知道每类来源为什么这么接入：读 `references/sources.md`

## 扩展方式

新增来源时按以下顺序做最小增量修改：

1. 在 `references/sources.json` 里新增来源条目
2. 如果已有抓取器足够，直接复用 `rss` / `github_releases` / `youtube_channel` 等
3. 如果没有合适抓取器，再补 `scripts/ai_news_digest.py` 的新 fetcher
4. 重新做至少两组验证

## 注意事项

- 该 Skill 当前优先保证“可运行、可验证、可扩展”，而不是覆盖所有站点的复杂私有接口
- 某些站点可能需要代理、证书、地区网络或额外凭据
- 若环境对某站点有限制，应继续输出已验证可抓的来源，并明确列出未命中或失败原因
