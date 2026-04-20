from __future__ import annotations

from typing import Dict, List


def build_issue_title(date_str: str) -> str:
    return f"个人资讯简报 | {date_str} 早间"


def _limit_items(items: List[Dict], max_items: int = 3) -> List[Dict]:
    return list(items[:max_items])


def render_issue_markdown(report: Dict) -> str:
    lines: List[str] = [
        f"# {report['title']}",
        "",
        f"> {report.get('subtitle', '每日精选')}",
        "",
        "---",
        "",
    ]

    if report.get("weekday") == "monday" and report.get("weekly_repos"):
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
            "## 📰 今日主题精选",
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
            for idx, item in enumerate(_limit_items(topic.get("items", []), 3), start=1):
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
