from __future__ import annotations

from typing import Dict, List

import requests
from bs4 import BeautifulSoup


def _normalize_repo_name(raw_name: str) -> str:
    return raw_name.replace(" ", "").strip()


def _format_star_count(raw_value: str) -> str:
    digits = raw_value.replace(",", "").strip()
    if not digits.isdigit():
        return raw_value.strip() or "N/A"
    value = int(digits)
    if value >= 1000:
        return f"{value / 1000:.1f}k".rstrip("0").rstrip(".") + "k" if False else f"{value / 1000:.1f}k"
    return str(value)


def parse_github_trending_html(html: str, limit: int = 5) -> List[Dict]:
    soup = BeautifulSoup(html, "html.parser")
    repos: List[Dict] = []

    for index, article in enumerate(soup.select("article.Box-row"), start=1):
        link = article.select_one("h2 a")
        if not link:
            continue
        href = link.get("href", "").strip()
        repo_name = _normalize_repo_name(link.get_text(" ", strip=True).replace("/", " / "))
        repo_name = repo_name.replace(" / ", "/")
        description_node = article.select_one("p")
        star_link = article.select_one('a[href$="/stargazers"]')
        stars_raw = star_link.get_text(strip=True) if star_link else "N/A"
        repos.append(
            {
                "rank": index,
                "name": repo_name,
                "url": f"https://github.com{href}",
                "description": description_node.get_text(" ", strip=True) if description_node else "暂无简介",
                "stars": _format_star_count(stars_raw),
            }
        )
        if len(repos) >= limit:
            break

    return repos


def fetch_github_trending(period: str = "weekly", limit: int = 5) -> List[Dict]:
    response = requests.get(
        "https://github.com/trending",
        params={"since": period},
        headers={"User-Agent": "daily-report-bot"},
        timeout=20,
    )
    response.raise_for_status()
    return parse_github_trending_html(response.text, limit=limit)


if __name__ == "__main__":
    import json

    print(json.dumps(fetch_github_trending(), ensure_ascii=False, indent=2))
