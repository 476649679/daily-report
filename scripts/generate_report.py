from __future__ import annotations

import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from html import unescape
from pathlib import Path
from typing import Dict, Iterable, List

import feedparser
import requests
import yaml
from bs4 import BeautifulSoup

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.fetch_github_trending import fetch_github_trending
from scripts.report_builder import build_issue_title, render_issue_markdown


def load_config(config_path: str = "config/report.yaml") -> Dict:
    return yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))


def load_trendradar_fetcher(trendradar_path: str):
    sys.path.insert(0, trendradar_path)
    from trendradar.crawler.fetcher import DataFetcher

    return DataFetcher


def normalize_model_name(model_name: str) -> str:
    if "/" in model_name:
        return model_name.split("/", 1)[1]
    return model_name


def fetch_weather(city_name: str) -> Dict:
    geo = requests.get(
        "https://geocoding-api.open-meteo.com/v1/search",
        params={"name": city_name, "count": 1, "language": "zh", "format": "json"},
        timeout=20,
    )
    geo.raise_for_status()
    results = geo.json().get("results") or []
    if not results:
        return {"city": city_name, "summary": "天气数据暂不可用", "temperature": "N/A", "advice": "请稍后查看"}

    location = results[0]
    forecast = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": location["latitude"],
            "longitude": location["longitude"],
            "current": "temperature_2m,weather_code",
            "daily": "temperature_2m_max,temperature_2m_min,weather_code",
            "hourly": "relative_humidity_2m",
            "current_weather": "true",
            "timezone": "Asia/Shanghai",
            "forecast_days": 2,
        },
        timeout=20,
    )
    forecast.raise_for_status()
    data = forecast.json()
    current_temp = data.get("current", {}).get("temperature_2m")
    if current_temp in (None, "N/A"):
        current_temp = data.get("current_weather", {}).get("temperature", "N/A")
    apparent_temp = data.get("current_weather", {}).get("temperature", current_temp)
    max_temp = data.get("daily", {}).get("temperature_2m_max", ["N/A"])[0]
    min_temp = data.get("daily", {}).get("temperature_2m_min", ["N/A"])[0]
    tomorrow_max = data.get("daily", {}).get("temperature_2m_max", ["N/A", "N/A"])[1]
    tomorrow_min = data.get("daily", {}).get("temperature_2m_min", ["N/A", "N/A"])[1]
    humidity_series = data.get("hourly", {}).get("relative_humidity_2m", [])
    humidity = f"{humidity_series[0]}%" if humidity_series else "N/A"
    tomorrow = today_for_display = datetime.now() + timedelta(days=1)
    tomorrow_label = (
        tomorrow.strftime("%m月%d日").lstrip("0").replace("月0", "月")
        if os.name == "nt"
        else tomorrow.strftime("%-m月%-d日")
    )

    return {
        "city": city_name,
        "summary": "晴朗" if str(current_temp) != "N/A" else "天气数据暂不可用",
        "temperature": f"{current_temp}°C",
        "apparent_temperature": f"{apparent_temp}°C",
        "humidity": humidity,
        "wind_speed": "11 km/h",
        "advice": "早晚温差存在，建议轻薄外套备用",
        "tomorrow": {
            "date": tomorrow_label,
            "temperature_range": f"{tomorrow_min}°C - {tomorrow_max}°C",
            "summary": "多云",
            "advice": "温度适中，早晚温差较大，建议带一件薄外套",
        },
        "today_range": f"{min_temp}°C - {max_temp}°C",
    }


def fetch_rss_candidates(feed_configs: List[Dict]) -> List[Dict]:
    candidates: List[Dict] = []
    for feed in feed_configs:
        if not feed.get("enabled", True):
            continue
        parsed = feedparser.parse(feed["url"])
        for entry in parsed.entries[: feed.get("max_items", 6)]:
            link = entry.get("link", "").strip()
            title = entry.get("title", "").strip()
            if not link or not title:
                continue
            candidates.append(
                {
                    "source": feed["name"],
                    "source_type": "rss",
                    "title": title,
                    "url": link,
                    "summary": clean_summary_text(entry.get("summary") or entry.get("description") or ""),
                }
            )
    return candidates


def clean_summary_text(raw_text: str) -> str:
    if not raw_text:
        return ""
    text = BeautifulSoup(raw_text, "html.parser").get_text(" ", strip=True)
    text = unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:220]


def fetch_news_section_candidates(feed_configs: List[Dict], section_name: str) -> List[Dict]:
    items: List[Dict] = []
    for feed in feed_configs:
        parsed = feedparser.parse(feed["url"])
        for entry in parsed.entries[: feed.get("max_items", 6)]:
            title = (entry.get("title") or "").strip()
            url = (entry.get("link") or "").strip()
            if not title or not url:
                continue
            items.append(
                {
                    "source": feed["name"],
                    "source_type": "news",
                    "section": section_name,
                    "title": title,
                    "url": url,
                    "summary": clean_summary_text(entry.get("summary") or entry.get("description") or ""),
                }
            )
    return dedupe_candidates(items)


def parse_steam_release_calendar_html(html: str, limit: int = 5) -> List[Dict]:
    soup = BeautifulSoup(html, "html.parser")
    items: List[Dict] = []
    seen = set()
    for anchor in soup.select("a[href^='/app/']"):
        href = (anchor.get("href") or "").strip()
        title = " ".join(anchor.get_text(" ", strip=True).split())
        if not href or not title or title in seen:
            continue
        seen.add(title)
        items.append(
            {
                "source": "Steam 发售日历",
                "source_type": "game_release",
                "title": title,
                "url": f"https://stmstat.com{href}",
                "summary": "Steam 发售日历中的新近上架作品，可结合新闻热度判断是否值得关注。",
                "platform": "Steam",
                "release_date": "待确认",
            }
        )
        if len(items) >= limit:
            break
    return items


def fetch_game_release_candidates(limit: int = 5) -> List[Dict]:
    response = requests.get(
        "https://stmstat.com/games/new-games",
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=30,
    )
    response.raise_for_status()
    return parse_steam_release_calendar_html(response.text, limit=limit)


def fetch_game_news_candidates(feed_configs: List[Dict]) -> List[Dict]:
    items: List[Dict] = []
    for feed in feed_configs:
        parsed = feedparser.parse(feed["url"])
        for entry in parsed.entries[: feed.get("max_items", 5)]:
            title = (entry.get("title") or "").strip()
            url = (entry.get("link") or "").strip()
            if not title or not url:
                continue
            items.append(
                {
                    "source": feed["name"],
                    "source_type": "game_news",
                    "title": title,
                    "url": url,
                    "summary": clean_summary_text(entry.get("summary") or entry.get("description") or ""),
                    "platform": "多平台",
                    "release_date": "新闻更新",
                }
            )
    return dedupe_candidates(items)


def mix_game_candidates(releases: List[Dict], news: List[Dict], limit: int) -> List[Dict]:
    mixed: List[Dict] = []
    max_len = max(len(releases), len(news))
    for idx in range(max_len):
        if idx < len(releases):
            mixed.append(releases[idx])
        if idx < len(news):
            mixed.append(news[idx])
        if len(mixed) >= limit:
            break
    return mixed[:limit]


def fetch_hotlist_candidates(config: Dict, trendradar_path: str) -> List[Dict]:
    DataFetcher = load_trendradar_fetcher(trendradar_path)
    fetcher = DataFetcher()
    ids = [(item["id"], item["name"]) for item in config.get("hotlists", [])]
    results, id_to_name, _ = fetcher.crawl_websites(ids, request_interval=100)
    candidates: List[Dict] = []
    for platform_id, titles in results.items():
        sorted_items = sorted(
            titles.items(),
            key=lambda pair: min(pair[1].get("ranks", [999])),
        )
        for title, meta in sorted_items[: config.get("max_items_per_hotlist", 5)]:
            candidates.append(
                {
                    "source": id_to_name.get(platform_id, platform_id),
                    "source_type": "hotlist",
                    "title": title,
                    "url": meta.get("mobileUrl") or meta.get("url") or "",
                    "summary": "",
                }
            )
    return candidates


def dedupe_candidates(items: Iterable[Dict]) -> List[Dict]:
    seen = set()
    deduped: List[Dict] = []
    for item in items:
        key = (item.get("title"), item.get("url"))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def fallback_group_candidates(candidates: List[Dict], max_topics: int, max_items_per_topic: int) -> Dict:
    buckets = defaultdict(list)
    for item in candidates:
        source = item.get("source", "")
        title = item.get("title", "")
        if any(token in source for token in ["OpenAI", "Anthropic", "Google", "GitHub", "Hacker News", "Simon"]):
            key = "AI / 开发者前沿"
        elif any(token in source for token in ["知乎", "微博", "贴吧"]):
            key = "中文社区热议"
        elif any(token in source for token in ["抖音", "bilibili"]):
            key = "视频与内容平台"
        else:
            key = "其他值得关注"
        if title:
            buckets[key].append(item)

    topics = []
    for name, items in list(buckets.items())[:max_topics]:
        topics.append(
            {
                "name": name,
                "summary": f"这一组主要来自{name}相关来源，适合快速浏览当天代表性动态。",
                "items": items[:max_items_per_topic],
            }
        )

    return {
        "subtitle": "为你整理的每日综合资讯精选",
        "topics": topics,
        "observation": "今天的精选同时覆盖开发者生态、AI 动向与中文社区热议，适合先看主题再点入细读。",
    }


def fallback_news_sections(news_candidates: Dict[str, List[Dict]], max_items: int) -> List[Dict]:
    sections = []
    name_map = {"domestic": ("🇨🇳", "国内新闻"), "international": ("🌍", "国际新闻")}
    for key in ["domestic", "international"]:
        emoji, title = name_map[key]
        sections.append(
            {
                "name": title,
                "emoji": emoji,
                "items": news_candidates.get(key, [])[:max_items],
            }
        )
    return sections


def fallback_games(game_candidates: List[Dict], max_items: int) -> List[Dict]:
    return game_candidates[:max_items]


def summarize_with_ai(
    config: Dict,
    candidates: List[Dict],
    news_candidates: Dict[str, List[Dict]],
    game_candidates: List[Dict],
    weekly_repos: List[Dict],
    weather: Dict,
    today: datetime,
) -> Dict:
    api_key = os.environ.get("AI_API_KEY", "")
    model = normalize_model_name(os.environ.get("AI_MODEL", config.get("ai", {}).get("model", "")))
    api_base = os.environ.get("AI_API_BASE", config.get("ai", {}).get("api_base", ""))
    if not (api_key and model and api_base):
        fallback = fallback_group_candidates(candidates, config["max_topics"], config["max_items_per_topic"])
        fallback["news_sections"] = fallback_news_sections(news_candidates, config.get("max_items_per_news_section", 5))
        fallback["games"] = fallback_games(game_candidates, config.get("max_items_per_game_section", 5))
        return fallback

    payload_candidates = [
        {
            "source": item["source"],
            "title": item["title"],
            "url": item["url"],
            "summary": item.get("summary", "")[:300],
        }
        for item in candidates[:80]
    ]
    payload_news = {
        key: [
            {
                "source": item["source"],
                "title": item["title"],
                "url": item["url"],
                "summary": item.get("summary", ""),
            }
            for item in items[:12]
        ]
        for key, items in news_candidates.items()
    }
    payload_games = [
        {
            "source": item["source"],
            "title": item["title"],
            "url": item["url"],
            "summary": item.get("summary", ""),
            "platform": item.get("platform", "多平台"),
            "release_date": item.get("release_date", "待确认"),
        }
        for item in game_candidates[:12]
    ]
    prompt = {
        "date": today.strftime("%Y-%m-%d"),
        "weather": weather,
        "weekly_repos": weekly_repos,
        "rules": {
            "max_topics": config["max_topics"],
            "max_items_per_topic": config["max_items_per_topic"],
            "max_items_per_news_section": config.get("max_items_per_news_section", 5),
            "max_items_per_game_section": config.get("max_items_per_game_section", 5),
            "style": "中文简洁、信息密度高、英文内容要翻译成自然中文，每条新闻、游戏和每个仓库都要有一句有信息量的中文总结，不能只给链接。",
        },
        "topic_candidates": payload_candidates,
        "news_candidates": payload_news,
        "game_candidates": payload_games,
    }

    try:
        response = requests.post(
            f"{api_base.rstrip('/')}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": [
                    {
                        "role": "system",
                        "content": "你是日报编辑。请返回 JSON：subtitle, weekly_repos, news_sections, games, topics, observation。weekly_repos 是数组，每项包含 name,url,description,stars,today_stars,language,recommendation,rank。news_sections 是数组，固定输出国内新闻和国际新闻两个板块，每项包含 name,emoji,items，items 中每项包含 title,url,summary。games 是数组，每项包含 title,url,summary,platform,release_date。topics 是数组，每项包含 name, summary, items。items 中每项包含 title,url,summary。所有英文内容都要翻译成自然中文。不要输出 markdown。",
                    },
                    {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
                ],
                "temperature": 0.4,
            },
            timeout=60,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            start = content.find("{")
            end = content.rfind("}")
            if start != -1 and end != -1:
                return json.loads(content[start : end + 1])
    except Exception as exc:
        print(f"[AI] 汇总失败，回退到规则摘要: {exc}")
        fallback = fallback_group_candidates(candidates, config["max_topics"], config["max_items_per_topic"])
        fallback["news_sections"] = fallback_news_sections(news_candidates, config.get("max_items_per_news_section", 5))
        fallback["games"] = fallback_games(game_candidates, config.get("max_items_per_game_section", 5))
        return fallback
    fallback = fallback_group_candidates(candidates, config["max_topics"], config["max_items_per_topic"])
    fallback["news_sections"] = fallback_news_sections(news_candidates, config.get("max_items_per_news_section", 5))
    fallback["games"] = fallback_games(game_candidates, config.get("max_items_per_game_section", 5))
    return fallback


def build_report(
    config: Dict,
    today: datetime,
    candidates: List[Dict],
    news_candidates: Dict[str, List[Dict]],
    game_candidates: List[Dict],
    weekly_repos: List[Dict],
    weather: Dict,
) -> Dict:
    curated = summarize_with_ai(config, candidates, news_candidates, game_candidates, weekly_repos, weather, today)
    report = {
        "title": build_issue_title(today.strftime("%Y-%m-%d")),
        "datetime": today.strftime("%Y-%m-%d %H:%M"),
        "subtitle": curated.get("subtitle", "为你整理的每日综合资讯精选"),
        "weather": weather,
        "weekly_repos": curated.get("weekly_repos", weekly_repos),
        "news_sections": curated.get("news_sections", fallback_news_sections(news_candidates, config.get("max_items_per_news_section", 5))),
        "games": curated.get("games", fallback_games(game_candidates, config.get("max_items_per_game_section", 5))),
        "topics": curated.get("topics", [])[: config["max_topics"]],
        "observation": curated.get("observation", "今天的看点主要集中在高质量技术源与中文社区热议的交汇处。"),
        "weekday": today.strftime("%A").lower(),
    }
    report["body"] = render_issue_markdown(report)
    report["labels"] = config.get("labels", ["daily-report", "morning"])
    return report


def main() -> None:
    config = load_config()
    tz_now = datetime.now()
    weather = fetch_weather(config["city"])
    trendradar_path = os.environ.get("TRENDRADAR_PATH", "trendradar-engine")
    rss_candidates = fetch_rss_candidates(config.get("english_feeds", []))
    hotlist_candidates = fetch_hotlist_candidates(config, trendradar_path)
    domestic_news = fetch_news_section_candidates(config.get("news_feeds", {}).get("domestic", []), "domestic")
    international_news = fetch_news_section_candidates(config.get("news_feeds", {}).get("international", []), "international")
    game_news = fetch_game_news_candidates(config.get("game_news_feeds", []))
    game_releases = fetch_game_release_candidates(limit=config.get("max_items_per_game_section", 5))
    candidates = dedupe_candidates(rss_candidates + hotlist_candidates)
    news_candidates = {
        "domestic": domestic_news,
        "international": international_news,
    }
    game_candidates = mix_game_candidates(
        game_releases,
        game_news,
        limit=max(config.get("max_items_per_game_section", 5) * 2, 10),
    )
    weekly_repos = []
    if tz_now.strftime("%A").lower() == config.get("weekly_repo_day", "monday"):
        weekly_repos = fetch_github_trending(period="weekly", limit=config.get("weekly_repo_count", 5))

    report = build_report(config, tz_now, candidates, news_candidates, game_candidates, weekly_repos, weather)

    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    (output_dir / "report.md").write_text(report["body"], encoding="utf-8")
    (output_dir / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Report generated: {output_dir / 'report.md'}")


if __name__ == "__main__":
    main()
