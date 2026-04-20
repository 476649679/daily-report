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
            lines.append(
                f"{repo['rank']}. [{repo['name']}]({repo['url']})"
            )
            lines.append(f"   - 功能：{repo.get('description', '暂无简介')}")
            lines.append(f"   - Stars：`{repo.get('stars', 'N/A')}`")
            lines.append(f"   - 排名：`#{repo['rank']}`")
            lines.append("")
        lines.extend(["---", ""])

    weather = report["weather"]
    lines.extend(
        [
            f"## 🌤️ {weather['city']}天气",
            "",
            f"**今日**：{weather['summary']} | {weather['temperature']}",
            f"👕 穿衣建议：{weather['advice']}",
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
            for item in _limit_items(topic.get("items", []), 3):
                lines.append(f"- [{item['title']}]({item['url']})")
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
