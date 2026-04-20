from __future__ import annotations

import json
import os
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List

import feedparser
import requests
import yaml

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
            "daily": "temperature_2m_max,temperature_2m_min",
            "timezone": "Asia/Shanghai",
            "forecast_days": 1,
        },
        timeout=20,
    )
    forecast.raise_for_status()
    data = forecast.json()
    current_temp = data.get("current", {}).get("temperature_2m", "N/A")
    max_temp = data.get("daily", {}).get("temperature_2m_max", ["N/A"])[0]
    min_temp = data.get("daily", {}).get("temperature_2m_min", ["N/A"])[0]
    return {
        "city": city_name,
        "summary": f"当前 {current_temp}°C，最高 {max_temp}°C / 最低 {min_temp}°C",
        "temperature": f"{current_temp}°C",
        "advice": "早晚温差存在，建议轻薄外套备用",
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
                    "summary": (entry.get("summary") or "").strip(),
                }
            )
    return candidates


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


def summarize_with_ai(config: Dict, candidates: List[Dict], weekly_repos: List[Dict], weather: Dict, today: datetime) -> Dict:
    api_key = os.environ.get("AI_API_KEY", "")
    model = os.environ.get("AI_MODEL", config.get("ai", {}).get("model", ""))
    api_base = os.environ.get("AI_API_BASE", config.get("ai", {}).get("api_base", ""))
    if not (api_key and model and api_base):
        return fallback_group_candidates(candidates, config["max_topics"], config["max_items_per_topic"])

    payload_candidates = [
        {
            "source": item["source"],
            "title": item["title"],
            "url": item["url"],
            "summary": item.get("summary", "")[:300],
        }
        for item in candidates[:80]
    ]
    prompt = {
        "date": today.strftime("%Y-%m-%d"),
        "weather": weather,
        "weekly_repos": weekly_repos,
        "rules": {
            "max_topics": config["max_topics"],
            "max_items_per_topic": config["max_items_per_topic"],
            "style": "中文简洁、信息密度高、每个主题一句总结、只保留最值得点开的链接",
        },
        "candidates": payload_candidates,
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
                        "content": "你是日报编辑。请返回 JSON：subtitle, topics, observation。topics 是数组，每项包含 name, summary, items。items 中每项包含 title, url。不要输出 markdown。",
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
        return fallback_group_candidates(candidates, config["max_topics"], config["max_items_per_topic"])
    return fallback_group_candidates(candidates, config["max_topics"], config["max_items_per_topic"])


def build_report(config: Dict, today: datetime, candidates: List[Dict], weekly_repos: List[Dict], weather: Dict) -> Dict:
    curated = summarize_with_ai(config, candidates, weekly_repos, weather, today)
    report = {
        "title": build_issue_title(today.strftime("%Y-%m-%d")),
        "datetime": today.strftime("%Y-%m-%d %H:%M"),
        "subtitle": curated.get("subtitle", "为你整理的每日综合资讯精选"),
        "weather": weather,
        "weekly_repos": weekly_repos,
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
    candidates = dedupe_candidates(rss_candidates + hotlist_candidates)
    weekly_repos = []
    if tz_now.strftime("%A").lower() == config.get("weekly_repo_day", "monday"):
        weekly_repos = fetch_github_trending(period="weekly", limit=config.get("weekly_repo_count", 5))

    report = build_report(config, tz_now, candidates, weekly_repos, weather)

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
