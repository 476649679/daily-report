# daily-report

一个轻量级的 GitHub 报刊仓库：同一个仓库里产出早报、午报和晚报三种 Issue。

## 内容结构

- 早报：天气、GitHub 热榜、新闻资讯、近期游戏、主题精选、今日观察
- 午报：社媒热议、今日热梗、轻量游戏动向、午间一刷
- 晚报：晚间游戏热点、视频与直播热议、今夜玩点啥、今日热梗回顾

## 数据来源

- 早报：
  - 高质量英文源：Hacker News、GitHub Changelog、OpenAI Blog、Anthropic News、Google AI Blog、Android Developers Blog、Simon Willison
  - 中文社区源：知乎、微博、贴吧、抖音、bilibili 热搜
  - GitHub Trending：每日热榜
- 午报 / 晚报：
  - TrendRadar 热榜骨架：微博、抖音、贴吧、bilibili 热搜、知乎
  - 娱乐补源：Google News 游戏、Steam、主机游戏、影视剧综、动漫二次元

## 必要 Secrets

- `AI_API_KEY`
- `AI_MODEL`
- `AI_API_BASE`

## 手动运行

进入仓库 `Actions`，按需要运行：

- `Morning Report`
- `Noon Report`
- `Evening Report`
