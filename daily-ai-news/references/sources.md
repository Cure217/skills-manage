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
| Anthropic Newsroom | 官方 | 页面解析 | 启用 | 官方新闻页，适合补充 Claude / 安全 / 产品更新 |
| Google AI Blog | 官方 | 页面解析 | 启用 | `blog.google/technology/ai/` |
| Google DeepMind Blog | 官方 | 页面解析 | 启用 | `deepmind.google/blog/` |
| Hugging Face Blog | 官方 / 社区 | RSS | 启用 | 生态更新、模型、平台能力 |
| GitHub Releases | 开源 | GitHub API | 启用 | 重点 AI 仓库版本更新 |
| GitHub Trending | 开源 | 页面解析 | 启用 | 当天热榜，按 AI 关键词做启发式过滤 |
| YouTube 官方频道 | 视频 | Channel Feed / Handle 解析 | 启用 | 可能受网络/TLS限制 |

## 默认保留为“可配置别名”的来源

### X(Twitter)

- 默认不直接内置抓取桥
- 原因：官方 API 通常需要凭据，第三方桥稳定性差异大
- 建议：在 `sources.json` 中填入自托管 RSSHub、企业中转服务或其他长期可维护桥接源

### B站

- 默认不内置具体账号或抓取接口
- 原因：不同账号需求差异大，公开接口稳定性和反爬策略变化较快
- 建议：按团队自己的账号清单配置可维护接口 / RSS / 中转源

### V站 / L站

- 按用户要求保留为“可配置来源别名”
- 默认不硬编码语义
- 你可以把它们映射成 Vimeo、Linux.do、V2EX 或团队自定义站点

## GitHub 重点仓库

当前默认覆盖：

- `openai/openai-python`
- `openai/openai-node`
- `huggingface/transformers`
- `vllm-project/vllm`
- `ollama/ollama`
- `langchain-ai/langchain`

如需扩展，直接修改 `references/sources.json` 即可。
