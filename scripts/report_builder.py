from __future__ import annotations

from typing import Dict, List


TITLE_TEMPLATES = {
    "morning": "个人资讯简报 | {date} 早间",
    "noon": "午间轻松报 | {date}",
    "evening": "夜间玩乐报 | {date}",
}


def build_issue_title(date_str: str, edition: str = "morning", template: str | None = None) -> str:
    title_template = template or TITLE_TEMPLATES.get(edition, TITLE_TEMPLATES["morning"])
    return title_template.format(date=date_str)


def render_entertainment_markdown(report: Dict) -> str:
    observation_title = report.get("observation_title") or (
        "午间观察" if report.get("edition") == "noon" else "夜间观察"
    )
    lines: List[str] = [
        f"# {report['title']}",
        "",
        f"> {report.get('subtitle', '今日娱乐休闲精选')}",
        "",
        "---",
        "",
    ]

    for section in report.get("sections", []):
        lines.append(f"## {section.get('emoji', '').strip()} {section['name']}".strip())
        lines.append("")
        items = section.get("items", [])
        if not items:
            lines.append("暂无值得收录的高热度内容。")
            lines.append("")
            continue
        for idx, item in enumerate(items, start=1):
            title = item["title"]
            if item.get("url"):
                title = f"[{title}]({item['url']})"
            summary = item.get("summary", "").strip()
            lines.append(f"{idx}. **{title}**{f' — {summary}' if summary else ''}")
            if item.get("meta"):
                lines.append(f"   - {item['meta']}")
        lines.append("")

    lines.extend(
        [
            "---",
            "",
            f"## 💡 {observation_title}",
            "",
            report.get("observation", "今天的轻松内容主要集中在高热度话题和适合碎片时间消费的娱乐项目上。"),
            "",
        ]
    )

    return "\n".join(lines).strip() + "\n"


def render_issue_markdown(report: Dict) -> str:
    if report.get("edition") in {"noon", "evening"}:
        return render_entertainment_markdown(report)

    lines: List[str] = [
        f"# {report['title']}",
        "",
        f"> {report.get('subtitle', '每日精选')}",
        "",
        "---",
        "",
    ]

    if report.get("weekly_repos"):
        lines.extend(["## 🔥 GitHub 仓库热榜推荐", ""])
        for repo in report["weekly_repos"]:
            lines.append(f"{repo['rank']}. **[{repo['name']}]({repo['url']})** — {repo.get('description', '暂无简介')}")
            stars_line = f"   - ⭐ 今日新增 {repo.get('today_stars', 'N/A')} | ⭐ 总 Star {repo.get('stars', 'N/A')}"
            if repo.get("language"):
                stars_line += f" | {repo['language']}"
            lines.append(stars_line)
            lines.append(f"   - 排名：`#{repo['rank']}`")
            if repo.get("recommendation"):
                lines.append(f"   - 推荐理由：{repo['recommendation']}")
            lines.append("")
        lines.extend(["---", ""])

    weather = report["weather"]
    lines.extend(
        [
            f"## 🌤️ 天气",
            "",
            "### 今日天气",
            f"- **温度**: {weather['temperature']}（体感 {weather.get('apparent_temperature', weather['temperature'])}）",
            f"- **天气**: {weather['summary']}",
            f"- **湿度**: {weather.get('humidity', 'N/A')}",
            f"- **风速**: {weather.get('wind_speed', 'N/A')}",
            "",
            f"### 明日预报（{weather.get('tomorrow', {}).get('date', '明日')}）",
            f"- **温度**: {weather.get('tomorrow', {}).get('temperature_range', 'N/A')}",
            f"- **天气**: {weather.get('tomorrow', {}).get('summary', 'N/A')}",
            f"- **建议**: {weather.get('tomorrow', {}).get('advice', weather['advice'])}",
            "",
            "---",
            "",
            "## 📰 新闻资讯",
            "",
        ]
    )

    for section in report.get("news_sections", []):
        header = f"### {section.get('emoji', '')} {section['name']}".strip()
        lines.append(header)
        lines.append("")
        for idx, item in enumerate(section.get("items", []), start=1):
            title = item["title"]
            if item.get("url"):
                title = f"[{title}]({item['url']})"
            summary = item.get("summary", "").strip()
            lines.append(f"{idx}. **{title}**{f' — {summary}' if summary else ''}")
            if item.get("meta"):
                lines.append(f"   - {item['meta']}")
        lines.append("")

    lines.extend(
        [
            "---",
            "",
            "## 🎮 近期游戏",
            "",
        ]
    )

    games = report.get("games") or []
    if not games:
        lines.extend(["近期暂无可用游戏资讯。", ""])
    else:
        for idx, item in enumerate(games, start=1):
            title = item["title"]
            if item.get("url"):
                title = f"[{title}]({item['url']})"
            lines.append(f"{idx}. **{title}** — {item.get('summary', '近期值得关注的游戏动态。')}")
            meta_parts = []
            if item.get("platform"):
                meta_parts.append(f"平台: {item['platform']}")
            if item.get("release_date"):
                meta_parts.append(f"发售: {item['release_date']}")
            if meta_parts:
                lines.append(f"   - {' | '.join(meta_parts)}")
        lines.append("")

    lines.extend(
        [
            "---",
            "",
            "## 🤖 今日主题精选",
            "",
        ]
    )

    topics = report.get("topics") or []
    if not topics:
        lines.extend(["今日暂无满足条件的精选主题。", ""])
    else:
        for topic in topics:
            lines.append(f"### {topic['name']}")
            lines.append("")
            lines.append(topic["summary"])
            lines.append("")
            for idx, item in enumerate(topic.get("items", []), start=1):
                title = item["title"]
                if item.get("url"):
                    title = f"[{title}]({item['url']})"
                lines.append(f"{idx}. **{title}**")
                if item.get("summary"):
                    lines.append(f"   - {item['summary']}")
            lines.append("")

    lines.extend(
        [
            "---",
            "",
            "## 💡 今日观察",
            "",
            report.get("observation", "今天整体走势平稳，建议优先关注高信号主题。"),
            "",
        ]
    )

    return "\n".join(lines).strip() + "\n"
