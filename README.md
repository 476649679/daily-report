# daily-report

一个轻量级的 GitHub 日报仓库：每天早上自动生成一条资讯精选 Issue。

## 内容结构

- 韶关天气
- GitHub 仓库热榜推荐（仅周一）
- 今日主题精选
- 今日观察

## 数据来源

- 高质量英文源：Hacker News、GitHub Changelog、OpenAI Blog、Anthropic News、Google AI Blog、Android Developers Blog、Simon Willison
- 中文社区源：知乎、微博、贴吧、抖音、bilibili 热搜
- GitHub Trending：周一推荐本周热门仓库

## 必要 Secrets

- `AI_API_KEY`
- `AI_MODEL`
- `AI_API_BASE`

## 手动运行

进入仓库 `Actions`，运行 `Morning Report`。
