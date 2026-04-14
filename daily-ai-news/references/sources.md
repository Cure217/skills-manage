# 默认来源说明

本 Skill 把来源设计成“可维护配置表 + 少量稳定抓取器”的模式，避免把大量站点规则硬编码在 `SKILL.md` 里。
机器可读配置在 `references/sources.json`。

## 接入优先级

1. 官方 API
2. RSS / Feed
3. 页面解析
4. GitHub Releases / Trending
5. 可配置来源别名

## 默认已启用来源

| 来源 | 类别 | 接入方式 | 默认状态 | 说明 |
| --- | --- | --- | --- | --- |
| OpenAI News | 官方 | RSS | 启用 | 一手官方动态 |
| Anthropic Newsroom | 官方 | 页面解析 | 启用 | 官方新闻页，补充 Claude / 安全 / 产品更新 |
| Anthropic Frontier Red Team | 官方 | 页面解析 | 启用 | 红队 / 安全研究更新 |
| Google AI Blog | 官方 | 页面解析 | 启用 | `blog.google/technology/ai/` |
| Google DeepMind Blog | 官方 | 页面解析 | 启用 | `deepmind.google/blog/` |
| Hugging Face Blog | 官方 / 社区 | RSS | 启用 | 生态、模型、平台能力更新 |
| GitHub Releases | 开源 | GitHub API / Atom | 启用 | 重点 AI 仓库版本更新 |
| GitHub Trending | 开源 | 页面解析 | 启用 | 当天热榜，按 AI 关键词做启发式过滤 |
| YouTube 官方频道 | 视频 | Channel Feed / Handle 解析 | 启用 | 可能受网络 / TLS 限制 |

## 固定别名映射

以下别名不是模糊占位，而是固定语义映射：

### B站

- 站点：`https://www.bilibili.com/`
- 默认语义：Bilibili 视频社区
- 当前状态：默认未启用，但已支持两种接入模式
- 方式一：`custom_rss`，适合团队自建 RSSHub、API 中转或稳定代理
- 方式二：`bilibili_up_videos`，适合按具体 AI UP 主直连抓取，推荐优先使用
- 直连规则：填写 `mid` 或 `space.bilibili.com/{mid}` 后，脚本会先拉 `https://www.bilibili.com/list/{mid}?sort_field=pubdate`，再调用公开视频详情接口补齐发布时间与简介
- 过滤方式：AI 关键词过滤

### V站

- 站点：`https://www.v2ex.com/`
- 默认语义：V2EX 社区
- 当前状态：已启用
- 当前规则：`https://www.v2ex.com/feed/tab/tech.xml`
- 过滤方式：RSS + AI 关键词过滤
- 说明：聚焦技术 tab，降低无关帖子噪音

### L站

- 站点：`https://linux.do/`
- 默认语义：Linux.do 社区
- 当前状态：已启用
- 当前规则：`https://linux.do/latest.rss`
- 过滤方式：RSS + AI 关键词过滤
- 说明：基于 latest.rss 拉取，再按 AI 关键词筛选相关讨论

### X(Twitter)

- 站点：`https://x.com/`
- 默认语义：X / Twitter
- 当前状态：待配置 / 未启用
- 原因：官方 API 通常需要凭据，第三方桥接稳定性差异较大

## 当前建议

- 如果只是做日常 AI 日报：优先依赖官方源、GitHub、YouTube
- 如果要把社区声音纳入日报：优先按团队需求补充 `B站 / V站 / L站 / X` 的稳定桥接
- 如果团队内部已经有 RSSHub、代理或 API 中转：优先把地址写进 `references/sources.json`
- 对 B站，优先使用 `bilibili_up_videos` 跟踪指定 AI UP 主，而不是直接抓全站搜索

## GitHub 重点仓库

当前默认覆盖：

- `openai/openai-python`
- `openai/openai-node`
- `huggingface/transformers`
- `vllm-project/vllm`
- `ollama/ollama`
- `langchain-ai/langchain`

如需扩展，直接修改 `references/sources.json` 即可。
