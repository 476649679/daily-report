from __future__ import annotations

import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from html import unescape
from pathlib import Path
from typing import Dict, Iterable, List
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import feedparser
import requests
import yaml
from bs4 import BeautifulSoup

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.fetch_github_trending import fetch_github_trending
from scripts.report_builder import build_issue_title, render_issue_markdown


EXCLUDED_GAME_KEYWORDS = [
    "🔞",
    "adult",
    "nsfw",
    "sex",
    "hentai",
    "ntr",
    "succubus",
    "nude",
    "fetish",
    "erotic",
    "soundtrack",
    "ost",
    "wallpaper",
    "playtest",
    "demo",
    "dlc",
    "midnight training",
    "bunny garden",
]

LOW_SIGNAL_NEWS_KEYWORDS = [
    "活动",
    "礼物",
    "见闻",
    "周末",
    "展演",
    "打卡",
    "读书",
    "文旅",
    "攻略",
    "图集",
    "写真",
    "花絮",
    "直播预告",
]

HARD_NEWS_KEYWORDS = [
    "地震",
    "战争",
    "袭击",
    "停火",
    "冲突",
    "关税",
    "油价",
    "制裁",
    "央行",
    "美联储",
    "国务院",
    "外交部",
    "宏观",
    "财政",
    "国债",
    "股市",
    "A股",
    "美股",
    "港股",
    "原油",
    "枪击",
    "空袭",
    "政策",
    "灾害",
    "灾难",
]

MAJOR_NEWS_KEYWORDS = [
    "特朗普",
    "伊朗",
    "以色列",
    "俄罗斯",
    "乌克兰",
    "关税",
    "停火",
    "袭击",
    "地震",
    "外交",
    "制裁",
    "油价",
    "枪击",
    "辞职",
    "协议",
    "战争",
    "危机",
]

DOMESTIC_PRIORITY_KEYWORDS = [
    "中国",
    "国内",
    "国务院",
    "外交部",
    "发改委",
    "商务部",
    "全国",
    "中央",
    "北京",
    "上海",
    "深圳",
    "香港",
]

INTERNATIONAL_PRIORITY_KEYWORDS = [
    "美国",
    "日本",
    "伊朗",
    "以色列",
    "俄罗斯",
    "乌克兰",
    "欧洲",
    "英国",
    "法国",
    "国际",
    "全球",
]

LOW_SIGNAL_GAME_NEWS_KEYWORDS = [
    "公告",
    "下架",
    "停售",
    "停服",
    "退款",
    "维护",
    "招募",
    "壁纸",
    "原声",
    "配乐",
    "试玩",
    "测试资格",
    "对接会",
    "对接大会",
    "峰会",
    "大会",
    "会议",
    "产业大会",
    "征文",
    "赛事报名",
]

MAJOR_GAME_KEYWORDS = [
    "Grand Theft Auto",
    "GTA",
    "血源",
    "Bloodborne",
    "Pragmata",
    "生化危机",
    "Resident Evil",
    "艾尔登法环",
    "Elden Ring",
    "巫师",
    "The Witcher",
    "赛博朋克",
    "Cyberpunk",
    "荒野大镖客",
    "Red Dead",
    "死亡搁浅",
    "Death Stranding",
    "怪物猎人",
    "Monster Hunter",
    "最终幻想",
    "Final Fantasy",
    "黑神话",
    "Black Myth",
    "刺客信条",
    "Assassin's Creed",
    "使命召唤",
    "Call of Duty",
    "Battlefield",
    "FIFA",
    "EA Sports FC",
    "文明",
    "Civilization",
    "暗黑破坏神",
    "Diablo",
    "宝可梦",
    "Pokemon",
    "塞尔达",
    "Zelda",
    "马里奥",
    "Mario",
]

PROTECTED_TERMS = [
    "Steam",
    "PlayStation",
    "Xbox",
    "Nintendo Switch",
    "PS5",
    "PS4",
    "Xbox Series X|S",
    "GitHub",
    "OpenAI",
    "Claude",
    "Android",
    "Google News",
    "BBC",
    "Le Monde",
    "GameSpot",
    "IGN",
    "Game Informer",
    "Hacker News",
    "GTA 6",
    "Grand Theft Auto VI",
    "Grand Theft Auto",
    "Pragmata",
    "Bloodborne",
    "Elden Ring",
    "Monster Hunter",
    "Resident Evil",
    "Cyberpunk 2077",
    "Death Stranding",
    "Final Fantasy",
    "Black Myth: Wukong",
    "Black Myth",
    "Draw Steel",
]

ENTERTAINMENT_BOOST_KEYWORDS = [
    "热搜",
    "爆火",
    "刷屏",
    "热议",
    "整活",
    "名场面",
    "二创",
    "玩梗",
    "综艺",
    "剧集",
    "电影",
    "动画",
    "新番",
    "直播",
    "主播",
    "视频",
]

MEME_KEYWORDS = [
    "梗",
    "表情包",
    "二创",
    "名场面",
    "抽象",
    "整活",
    "玩梗",
    "吐槽",
    "meme",
]

VIDEO_KEYWORDS = [
    "视频",
    "短片",
    "直播",
    "UP主",
    "主播",
    "B站",
    "抖音",
    "名场面",
    "综艺",
    "剧集",
    "电影",
    "动漫",
    "新番",
]

SERIOUS_SOCIAL_KEYWORDS = [
    "烈士",
    "志愿军",
    "国台办",
    "统一",
    "英雄",
    "回家",
    "国务院",
    "国民经济",
    "服务业",
    "外交",
    "事故",
    "隐患",
    "安全",
    "时政",
    "央视",
    "网警",
]

LIGHT_ENTERTAINMENT_KEYWORDS = [
    "综艺",
    "剧",
    "电影",
    "演员",
    "明星",
    "恋情",
    "乐队",
    "演唱会",
    "直播",
    "UP主",
    "主播",
    "球员",
    "比赛",
    "新番",
    "动漫",
    "二创",
    "名场面",
    "游戏",
]

PROMOTIONAL_KEYWORDS = [
    "招商",
    "开幕",
    "发布会",
    "官宣海报",
    "预热",
    "报名",
    "福利",
    "抽奖",
    "联动活动",
    "品牌活动",
]

TERM_CORRECTIONS = {
    "蒸汽": "Steam",
    "拉钢": "Draw Steel",
    "开放人工智能": "OpenAI",
}

DOMESTIC_NEWS_MIN_ITEMS = 2
DOMESTIC_NEWS_MAX_ITEMS = 8
INTERNATIONAL_NEWS_MIN_ITEMS = 2
INTERNATIONAL_NEWS_MAX_ITEMS = 8
GAME_MIN_ITEMS = 3
GAME_MAX_ITEMS = 8
GITHUB_REPO_MIN_ITEMS = 3
GITHUB_REPO_MAX_ITEMS = 8
TOPIC_ITEMS_MAX = 6

DEFAULT_EDITION_SETTINGS = {
    "morning": {
        "title_template": "个人资讯简报 | {date} 早间",
        "labels": ["daily-report", "morning"],
        "subtitle": "为你整理的每日综合资讯精选",
        "include_weather": True,
        "observation_title": "今日观察",
    },
    "noon": {
        "title_template": "午间轻松报 | {date}",
        "labels": ["daily-report", "noon", "entertainment"],
        "subtitle": "中午适合快速刷一遍的娱乐休闲精选",
        "include_weather": False,
        "observation_title": "午间观察",
        "sections": [
            {"key": "social", "name": "社媒热议", "emoji": "📱"},
            {"key": "memes", "name": "今日热梗", "emoji": "🤣"},
            {"key": "games", "name": "轻量游戏动向", "emoji": "🎮"},
            {"key": "picks", "name": "午间一刷", "emoji": "✨"},
        ],
    },
    "evening": {
        "title_template": "夜间玩乐报 | {date}",
        "labels": ["daily-report", "evening", "entertainment"],
        "subtitle": "今晚值得一口气看完的轻松内容和热门游戏动向",
        "include_weather": False,
        "observation_title": "夜间观察",
        "sections": [
            {"key": "games", "name": "晚间游戏热点", "emoji": "🎮"},
            {"key": "video", "name": "视频与直播热议", "emoji": "📺"},
            {"key": "night_picks", "name": "今夜玩点啥", "emoji": "🌙"},
            {"key": "memes", "name": "今日热梗回顾", "emoji": "🤣"},
        ],
    },
}


def load_config(config_path: str = "config/report.yaml") -> Dict:
    return yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))


def get_edition_settings(config: Dict, edition: str) -> Dict:
    base = dict(DEFAULT_EDITION_SETTINGS.get(edition, DEFAULT_EDITION_SETTINGS["morning"]))
    override = config.get("editions", {}).get(edition, {})
    base.update(override)
    base["edition"] = edition
    return base


def load_trendradar_fetcher(trendradar_path: str):
    sys.path.insert(0, trendradar_path)
    from trendradar.crawler.fetcher import DataFetcher

    return DataFetcher


def normalize_model_name(model_name: str) -> str:
    if "/" in model_name:
        return model_name.split("/", 1)[1]
    return model_name


def get_now_in_timezone(timezone_name: str, now: datetime | None = None) -> datetime:
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    try:
        zone = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        fallback_offsets = {
            "Asia/Shanghai": timezone(timedelta(hours=8)),
        }
        zone = fallback_offsets.get(timezone_name, timezone.utc)
    return current.astimezone(zone)


def fetch_weather(city_name: str, timezone_name: str = "Asia/Shanghai") -> Dict:
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
    tomorrow = get_now_in_timezone(timezone_name) + timedelta(days=1)
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


def parse_entry_datetime(entry) -> str:
    parsed = (
        entry.get("published_parsed")
        or entry.get("updated_parsed")
        or entry.get("created_parsed")
    )
    if not parsed:
        return ""
    return datetime(*parsed[:6], tzinfo=timezone.utc).isoformat()


def first_sentence(summary: str) -> str:
    text = (summary or "").strip()
    if not text:
        return ""
    match = re.search(r"^.*?[。！？.!?]", text)
    sentence = match.group(0).strip() if match else text
    return sentence[:120]


def normalize_entertainment_title(title: str) -> str:
    cleaned = translate_text_to_zh(title or "")
    cleaned = re.sub(r"\s*[-|｜–—]\s*[^-|｜–—]{1,20}$", "", cleaned).strip()
    cleaned = re.sub(r"_[^_]{1,20}$", "", cleaned).strip()
    cleaned = cleaned.replace("： ", "：").replace("  ", " ").strip(" -|｜–—")
    return cleaned


def heuristic_entertainment_summary(title: str, section_key: str) -> str:
    normalized_title = normalize_entertainment_title(title)

    title_rules = [
        (r"获刑|判刑|被判", "讨论焦点在判决结果已经落地，大家更关心这件事后续会怎样影响当事人的口碑和走向。"),
        (r"退款|退费|押金|维权", "这条热议主要围绕维权和退款争议发酵，讨论点集中在责任归属和处理方式是否合理。"),
        (r"免费|免单|福利", "吸引大家点开的核心就是福利和门槛，评论区更多是在问入口、真假和能不能薅到。"),
        (r"涨价|变贵", "这条内容的热度来自价格变动本身，大家主要在讨论会不会继续影响日常消费选择。"),
        (r"合作|联动|共同开发", "这条话题把跨界合作的想象空间拉满，讨论基本都围绕新玩法和后续落地可能性展开。"),
        (r"击败|战胜|扳平|绝杀|夺冠", "比赛结果本身就很能带动讨论，大家更关注关键回合、选手表现和后续走势。"),
        (r"新史低|史低|促销|打折|折扣", "这条内容值得看主要因为折扣力度够大，评论区更像在交流现在到底值不值得入手。"),
        (r"片单|官宣|常驻|阵容|预告", "大家关注的重点是新项目和阵容安排，热度基本来自对后续上线表现的期待。"),
        (r"新番|动漫|配音|角色|二创", "这条内容的讨论点更多落在作品角色和圈层热度延续上，适合顺手补一眼。"),
        (r"直播|主播|UP主|视频", "热度主要来自内容本身适合传播，大家更关心有没有名场面和值不值得点开。"),
        (r"模型|AI|Cursor|SpaceX", "这条能冲上来，核心还是题材够新又够跨界，讨论基本都围绕它会带来什么新变化。"),
    ]
    for pattern, summary in title_rules:
        if re.search(pattern, normalized_title, re.IGNORECASE):
            return summary

    if section_key == "social":
        return f"这条热议主要是因为话题本身够抓眼球，大家在讨论它为什么会突然冲上今天的社媒版面。"
    if section_key == "memes":
        return "这个梗能留下来，说明它已经不只是单点吐槽，而是开始往更广的圈层扩散。"
    if section_key == "games":
        return "这条游戏动态之所以值得看，是因为它和今天玩家最关心的作品、价格或后续动作直接相关。"
    if section_key in {"video", "night_picks", "picks"}:
        return "这条内容更适合碎片时间点开，因为它本身就代表了今天娱乐话题里最容易出圈的一类。"
    return "这条内容今天讨论度比较靠前，适合快速了解大家正在关注什么。"


def is_english_heavy(text: str) -> bool:
    if not text:
        return False
    ascii_letters = sum(1 for ch in text if "a" <= ch.lower() <= "z")
    cjk = sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff")
    return ascii_letters > cjk


def protect_terms_for_translation(text: str, extra_terms: Iterable[str] | None = None) -> tuple[str, Dict[str, str]]:
    if not text:
        return text, {}

    protected = text
    placeholders: Dict[str, str] = {}
    terms = sorted(
        {term for term in [*PROTECTED_TERMS, *(extra_terms or [])] if term},
        key=len,
        reverse=True,
    )

    for term in terms:
        pattern = re.compile(re.escape(term), re.IGNORECASE)

        def replacer(match, *, _term=term):
            token = f"ZXQPROTECTTOKEN{len(placeholders)}QXZ"
            placeholders[token] = match.group(0)
            return token

        protected = pattern.sub(replacer, protected)

    return protected, placeholders


def restore_protected_terms(text: str, placeholders: Dict[str, str]) -> str:
    restored = text
    for token, value in placeholders.items():
        restored = restored.replace(token, value)
        restored = restored.replace(token.replace("PROTECTTOKEN", "保护令牌"), value)
    for wrong, correct in TERM_CORRECTIONS.items():
        restored = restored.replace(wrong, correct)
    return restored


def dynamic_keep_count(scores: List[int], min_items: int, max_items: int, ratio: float, floor: int) -> int:
    if not scores:
        return 0
    top_score = scores[0]
    threshold = max(int(top_score * ratio), floor)
    count = 0
    for score in scores:
        if count < min_items or score >= threshold:
            count += 1
        else:
            break
    return min(max(count, min_items), min(max_items, len(scores)))


def translate_text_to_zh(text: str) -> str:
    if not text or not is_english_heavy(text):
        return text
    protected_text, placeholders = protect_terms_for_translation(text)
    try:
        response = requests.get(
            "https://translate.googleapis.com/translate_a/single",
            params={
                "client": "gtx",
                "sl": "auto",
                "tl": "zh-CN",
                "dt": "t",
                "q": protected_text,
            },
            timeout=20,
        )
        response.raise_for_status()
        data = response.json()
        parts = []
        for part in data[0]:
            if part and part[0]:
                parts.append(part[0])
        translated = "".join(parts).strip()
        translated = restore_protected_terms(translated, placeholders)
        return translated or text
    except Exception:
        return restore_protected_terms(protected_text, placeholders)


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
                    "published_at": parse_entry_datetime(entry),
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


def is_excluded_game_candidate(item: Dict) -> bool:
    haystack = f"{item.get('title', '')} {item.get('summary', '')}".lower()
    return any(keyword in haystack for keyword in EXCLUDED_GAME_KEYWORDS) or any(
        keyword in haystack for keyword in [word.lower() for word in LOW_SIGNAL_GAME_NEWS_KEYWORDS]
    )


def game_candidate_score(item: Dict) -> int:
    haystack = f"{item.get('title', '')} {item.get('summary', '')}".lower()
    score = 0
    if item.get("source_type") == "game_news":
        score += 120
    else:
        score += 20
    if str(item.get("source", "")).startswith("Google News"):
        score += 30
    if item.get("source") == "Steam 发售日历":
        score += 10
    title = item.get("title", "")
    if 4 <= len(title) <= 40:
        score += 10
    if any(keyword.lower() in haystack for keyword in MAJOR_GAME_KEYWORDS):
        score += 90
    if any(keyword.lower() in haystack for keyword in LOW_SIGNAL_GAME_NEWS_KEYWORDS):
        score -= 120
    if re.search(r"\b(review|preview|trailer|release date|launch|销量|评测|实机|预告|发售)\b", haystack):
        score += 40
    if re.search(r"\b(indie|demo|soundtrack|wallpaper|maintenance|refund)\b", haystack):
        score -= 60
    if re.search(r"[🔞✨❤♡★☆]", title):
        score -= 50
    if re.search(r"[!@#$%^&*]{2,}", title):
        score -= 20
    if len(re.findall(r"[A-Z]{3,}", title)) >= 2:
        score -= 10
    return score


def curate_game_candidates(releases: List[Dict], news: List[Dict], limit: int) -> List[Dict]:
    filtered_releases = [item for item in releases if not is_excluded_game_candidate(item)]
    filtered_news = [item for item in news if not is_excluded_game_candidate(item)]
    filtered_releases.sort(key=game_candidate_score, reverse=True)
    filtered_news.sort(key=game_candidate_score, reverse=True)

    curated: List[Dict] = []
    max_len = max(len(filtered_news), len(filtered_releases))
    for idx in range(max_len):
        if idx < len(filtered_news):
            curated.append(filtered_news[idx])
        if idx < len(filtered_releases):
            curated.append(filtered_releases[idx])
        if len(curated) >= limit * 2:
            break
    curated = dedupe_candidates(curated)
    curated = [item for item in curated if game_candidate_score(item) >= 40]
    curated.sort(key=game_candidate_score, reverse=True)
    scores = [game_candidate_score(item) for item in curated]
    keep_count = dynamic_keep_count(scores, GAME_MIN_ITEMS, min(limit, GAME_MAX_ITEMS), ratio=0.55, floor=70)
    return curated[:keep_count]


def fetch_hotlist_candidates(config: Dict, trendradar_path: str, hotlist_configs: List[Dict] | None = None) -> List[Dict]:
    DataFetcher = load_trendradar_fetcher(trendradar_path)
    fetcher = DataFetcher()
    ids = [(item["id"], item["name"]) for item in (hotlist_configs or config.get("hotlists", []))]
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


def is_hard_news_item(item: Dict) -> bool:
    haystack = f"{item.get('title', '')} {item.get('summary', '')}".lower()
    return any(keyword.lower() in haystack for keyword in HARD_NEWS_KEYWORDS)


def build_entertainment_summary(item: Dict, section_key: str) -> str:
    summary = first_sentence(translate_text_to_zh(item.get("summary", ""))).strip()
    source = item.get("source", "平台")
    title = normalize_entertainment_title(item.get("title", ""))
    if summary:
        return summary

    heuristic = heuristic_entertainment_summary(title, section_key)
    if heuristic:
        return heuristic

    if section_key == "social":
        return f"这条内容在 {source} 上扩散很快，也把评论区的讨论重点迅速带到了更多人面前。"
    if section_key == "memes":
        return "这个梗今天讨论度很高，已经从单点话题扩散到多个平台。"
    if section_key == "games":
        if any(keyword.lower() in f"{title} {source}".lower() for keyword in MAJOR_GAME_KEYWORDS):
            return f"{title} 这条动态更偏高认知游戏热点，讨论焦点集中在它接下来还能不能继续抬高关注度。"
        return "这条游戏内容讨论度靠前，适合快速了解今天玩家最在意的是新品、价格还是后续更新。"
    if section_key in {"video", "night_picks", "picks"}:
        return "这条内容更适合碎片时间点开，看完就能跟上今天娱乐话题里最容易出圈的方向。"
    return f"这条内容今天讨论度较高，适合快速浏览。"


def entertainment_candidate_score(item: Dict, section_key: str) -> int:
    haystack = f"{item.get('title', '')} {item.get('summary', '')}".lower()
    if is_hard_news_item(item):
        return -200

    score = 0
    source = item.get("source", "")
    source_type = item.get("source_type", "")

    source_scores = {
        "微博": 70,
        "抖音": 68,
        "bilibili 热搜": 66,
        "贴吧": 52,
        "知乎": 22,
    }
    score += source_scores.get(source, 12)

    if source_type == "hotlist":
        score += 25
    if source_type == "game_news":
        score += 35
    if source_type == "game_release":
        score += 18
    if source_type == "rss":
        score += 20

    if any(keyword.lower() in haystack for keyword in ENTERTAINMENT_BOOST_KEYWORDS):
        score += 38
    if any(keyword.lower() in haystack for keyword in PROMOTIONAL_KEYWORDS):
        score -= 45
    if any(keyword.lower() in haystack for keyword in SERIOUS_SOCIAL_KEYWORDS):
        score -= 120

    if section_key == "social":
        if source in {"微博", "抖音", "bilibili 热搜", "贴吧"}:
            score += 45
        if any(keyword.lower() in haystack for keyword in MEME_KEYWORDS):
            score += 15
        if not any(keyword.lower() in haystack for keyword in LIGHT_ENTERTAINMENT_KEYWORDS + MEME_KEYWORDS + VIDEO_KEYWORDS):
            score -= 35
    elif section_key == "memes":
        if any(keyword.lower() in haystack for keyword in MEME_KEYWORDS):
            score += 60
        if source in {"微博", "抖音", "bilibili 热搜", "贴吧"}:
            score += 20
        if not any(keyword.lower() in haystack for keyword in MEME_KEYWORDS + LIGHT_ENTERTAINMENT_KEYWORDS):
            score -= 50
    elif section_key == "games":
        if any(keyword.lower() in haystack for keyword in MAJOR_GAME_KEYWORDS):
            score += 90
        if any(token in source for token in ["游戏", "Steam", "主机"]):
            score += 35
        if any(keyword.lower() in haystack for keyword in LOW_SIGNAL_GAME_NEWS_KEYWORDS):
            score -= 80
    elif section_key == "video":
        if any(keyword.lower() in haystack for keyword in VIDEO_KEYWORDS):
            score += 55
        if source in {"抖音", "bilibili 热搜", "微博"}:
            score += 20
        if not any(keyword.lower() in haystack for keyword in VIDEO_KEYWORDS + LIGHT_ENTERTAINMENT_KEYWORDS + MEME_KEYWORDS):
            score -= 55
    elif section_key in {"night_picks", "picks"}:
        if any(keyword.lower() in haystack for keyword in VIDEO_KEYWORDS + ENTERTAINMENT_BOOST_KEYWORDS):
            score += 30
        if any(keyword.lower() in haystack for keyword in MAJOR_GAME_KEYWORDS):
            score += 25
        if not any(keyword.lower() in haystack for keyword in VIDEO_KEYWORDS + LIGHT_ENTERTAINMENT_KEYWORDS + MAJOR_GAME_KEYWORDS + MEME_KEYWORDS):
            score -= 60

    return score


def curate_social_items(items: List[Dict], min_items: int = 3, max_items: int = 8) -> List[Dict]:
    curated = [item for item in items if entertainment_candidate_score(item, "social") > 0]
    curated.sort(key=lambda item: entertainment_candidate_score(item, "social"), reverse=True)
    scores = [entertainment_candidate_score(item, "social") for item in curated]
    keep_count = dynamic_keep_count(scores, min_items, max_items, ratio=0.55, floor=65)
    return curated[:keep_count]


def pick_entertainment_items(
    candidates: List[Dict],
    section_key: str,
    used_keys: set[tuple[str, str]],
    min_items: int = 3,
    max_items: int = 8,
) -> List[Dict]:
    ranked = []
    for item in candidates:
        key = (item.get("title", ""), item.get("url", ""))
        if key in used_keys:
            continue
        score = entertainment_candidate_score(item, section_key)
        if score <= 0:
            continue
        ranked.append((score, item))

    ranked.sort(key=lambda pair: pair[0], reverse=True)
    scores = [score for score, _ in ranked]
    if not scores:
        return []
    keep_count = dynamic_keep_count(scores, min_items, max_items, ratio=0.55, floor=55)
    selected = []
    for _, item in ranked[:keep_count]:
        key = (item.get("title", ""), item.get("url", ""))
        used_keys.add(key)
        selected.append(
            {
                "title": translate_text_to_zh(item.get("title", "")),
                "url": item.get("url", ""),
                "summary": build_entertainment_summary(item, section_key),
                "meta": f"来源：{item.get('source', '资讯源')}",
            }
        )
    return selected


def build_entertainment_observation(edition: str, sections: List[Dict]) -> str:
    populated = [section["name"] for section in sections if section.get("items")]
    if not populated:
        return "这一期没有足够高热度的娱乐休闲内容，宁可少发也不硬凑。"
    if edition == "noon":
        return f"今天中午最有存在感的是{'、'.join(populated[:2])}，整体更偏适合碎片时间快速刷完的轻松内容。"
    return f"今晚的重心集中在{'、'.join(populated[:2])}，更适合下班后或睡前集中补完。"


def build_edition_report(
    config: Dict,
    edition: str,
    today: datetime,
    weather: Dict | None,
    sections: List[Dict],
    weekly_repos: List[Dict],
    observation: str,
) -> Dict:
    settings = get_edition_settings(config, edition)
    title = build_issue_title(today.strftime("%Y-%m-%d"), edition=edition, template=settings.get("title_template"))
    report = {
        "edition": edition,
        "title": title,
        "datetime": today.strftime("%Y-%m-%d %H:%M"),
        "subtitle": settings.get("subtitle", "每日精选"),
        "weekly_repos": weekly_repos,
        "sections": sections,
        "observation_title": settings.get("observation_title", "今日观察"),
        "observation": observation,
        "labels": settings.get("labels", ["daily-report"]),
        "include_weather": settings.get("include_weather", True),
    }
    if report["include_weather"] and weather is not None:
        report["weather"] = weather
    report["body"] = render_issue_markdown(report)
    return report


def news_candidate_score(item: Dict, section: str = "") -> int:
    score = 0
    haystack = f"{item.get('title', '')} {item.get('summary', '')}"
    if item.get("source", "").startswith("Google News"):
        score += 40
    elif item.get("source") in {"BBC World", "Le Monde International"}:
        score += 30
    elif item.get("source") == "中新网滚动":
        score += 20

    lowered = haystack.lower()
    if any(keyword.lower() in lowered for keyword in MAJOR_NEWS_KEYWORDS):
        score += 50
    if any(keyword.lower() in lowered for keyword in LOW_SIGNAL_NEWS_KEYWORDS):
        score -= 60
    if section == "domestic":
        if any(keyword.lower() in lowered for keyword in DOMESTIC_PRIORITY_KEYWORDS):
            score += 35
        if any(keyword.lower() in lowered for keyword in INTERNATIONAL_PRIORITY_KEYWORDS):
            score -= 45
    if section == "international":
        if any(keyword.lower() in lowered for keyword in INTERNATIONAL_PRIORITY_KEYWORDS):
            score += 35
        if any(keyword.lower() in lowered for keyword in DOMESTIC_PRIORITY_KEYWORDS):
            score -= 30

    published_at = item.get("published_at") or ""
    if published_at:
        try:
            published_dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
            if published_dt.tzinfo is None:
                published_dt = published_dt.replace(tzinfo=timezone.utc)
            age_hours = max(0.0, (datetime.now(timezone.utc) - published_dt).total_seconds() / 3600)
            score += max(0, int(48 - min(age_hours, 48)))
        except ValueError:
            pass
    return score


def curate_news_candidates(items: List[Dict], limit: int, section: str = "") -> List[Dict]:
    curated = []
    for item in items:
        summary = first_sentence(item.get("summary", ""))
        normalized = {**item, "summary": summary}
        lowered = f"{normalized.get('title', '')} {normalized.get('summary', '')}".lower()
        if section == "domestic":
            has_domestic = any(keyword.lower() in lowered for keyword in DOMESTIC_PRIORITY_KEYWORDS)
            has_international = any(keyword.lower() in lowered for keyword in INTERNATIONAL_PRIORITY_KEYWORDS)
            if has_international and not has_domestic:
                continue
        if section == "international":
            has_domestic = any(keyword.lower() in lowered for keyword in DOMESTIC_PRIORITY_KEYWORDS)
            has_international = any(keyword.lower() in lowered for keyword in INTERNATIONAL_PRIORITY_KEYWORDS)
            if has_domestic and not has_international:
                continue
        if news_candidate_score(normalized, section=section) < 0:
            continue
        curated.append(normalized)
    curated.sort(key=lambda item: news_candidate_score(item, section=section), reverse=True)
    scores = [news_candidate_score(item, section=section) for item in curated]
    if section == "domestic":
        keep_count = dynamic_keep_count(scores, DOMESTIC_NEWS_MIN_ITEMS, min(limit, DOMESTIC_NEWS_MAX_ITEMS), ratio=0.5, floor=80)
    else:
        keep_count = dynamic_keep_count(scores, INTERNATIONAL_NEWS_MIN_ITEMS, min(limit, INTERNATIONAL_NEWS_MAX_ITEMS), ratio=0.5, floor=75)
    return curated[:keep_count]


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
        limited_items = items[: min(max_items_per_topic, TOPIC_ITEMS_MAX)]
        topics.append(
            {
                "name": name,
                "summary": f"这一组主要来自{name}相关来源，适合快速浏览当天代表性动态。",
                "items": limited_items,
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
                "items": curate_news_candidates(news_candidates.get(key, []), max_items, section=key),
            }
        )
    return sections


def fallback_games(game_candidates: List[Dict], max_items: int) -> List[Dict]:
    return game_candidates[:max_items]


def parse_metric_value(raw_value: str) -> int:
    text = str(raw_value or "").strip().lower().replace(",", "")
    if not text:
        return 0
    match = re.match(r"(\d+(?:\.\d+)?)(k)?", text)
    if not match:
        return 0
    value = float(match.group(1))
    if match.group(2):
        value *= 1000
    return int(value)


def github_repo_score(repo: Dict) -> int:
    score = 0
    score += parse_metric_value(repo.get("today_stars", ""))
    score += parse_metric_value(repo.get("stars", "")) // 10
    rank = int(repo.get("rank", 99))
    score += max(0, 120 - rank * 10)
    return score


def curate_github_repos(repos: List[Dict], limit: int) -> List[Dict]:
    ranked = sorted(repos, key=github_repo_score, reverse=True)
    scores = [github_repo_score(repo) for repo in ranked]
    keep_count = dynamic_keep_count(scores, GITHUB_REPO_MIN_ITEMS, min(limit, GITHUB_REPO_MAX_ITEMS), ratio=0.45, floor=80)
    curated = ranked[:keep_count]
    for idx, repo in enumerate(curated, start=1):
        repo["rank"] = idx
    return curated


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
        fallback["weekly_repos"] = weekly_repos
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
            "max_items_per_news_section": config.get("max_items_per_news_section", DOMESTIC_NEWS_MAX_ITEMS),
            "max_items_per_game_section": config.get("max_items_per_game_section", GAME_MAX_ITEMS),
            "max_items_per_repo_section": config.get("weekly_repo_count", GITHUB_REPO_MAX_ITEMS),
            "style": "中文简洁、信息密度高、英文内容要翻译成自然中文，每条新闻、游戏和每个仓库都要有一句有信息量的中文总结，不能只给链接。条目数按热度动态增减，不要为了凑数硬塞低热度内容。游戏板块只保留认知度高的大型热门游戏。Steam、GitHub、OpenAI、Claude、Android、GTA 6、Pragmata 等专有名词保留原名。",
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
                        "content": "你是日报编辑。请返回 JSON：subtitle, weekly_repos, news_sections, games, topics, observation。weekly_repos 是数组，每项包含 name,url,description,stars,today_stars,language,recommendation,rank。news_sections 是数组，固定输出国内新闻和国际新闻两个板块，每项包含 name,emoji,items，items 中每项包含 title,url,summary。games 是数组，每项包含 title,url,summary,platform,release_date。topics 是数组，每项包含 name, summary, items。items 中每项包含 title,url,summary。所有英文内容都要翻译成自然中文，但 Steam、GitHub、OpenAI、Claude、Android、GTA 6、Pragmata 等专有名词保留原名。每条 summary 压成一句话，不要输出 markdown。",
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
        fallback["weekly_repos"] = weekly_repos
        return fallback
    fallback = fallback_group_candidates(candidates, config["max_topics"], config["max_items_per_topic"])
    fallback["news_sections"] = fallback_news_sections(news_candidates, config.get("max_items_per_news_section", 5))
    fallback["games"] = fallback_games(game_candidates, config.get("max_items_per_game_section", 5))
    fallback["weekly_repos"] = weekly_repos
    return fallback


def localize_report_content(report: Dict) -> Dict:
    api_key = os.environ.get("AI_API_KEY", "")
    model = normalize_model_name(os.environ.get("AI_MODEL", ""))
    api_base = os.environ.get("AI_API_BASE", "")
    if not (api_key and model and api_base):
        return report

    payload = {
        "weekly_repos": report.get("weekly_repos", []),
        "news_sections": report.get("news_sections", []),
        "games": report.get("games", []),
        "topics": report.get("topics", []),
        "observation": report.get("observation", ""),
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
                        "content": "你是资讯编辑。请把输入 JSON 中所有英文标题、英文摘要、英文描述翻译成自然中文；已经是中文的内容保持中文优化即可。news_sections、games、topics 中每条 summary 都压缩成一句话，weekly_repos 的 description 和 recommendation 也用简洁中文。Steam、GitHub、OpenAI、Claude、Android、GTA 6、Pragmata 等专有名词保留原名。保持原有字段和 URL，不要新增字段，不要输出 markdown，只返回 JSON。",
                    },
                    {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
                ],
                "temperature": 0.2,
            },
            timeout=60,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        try:
            localized = json.loads(content)
        except json.JSONDecodeError:
            start = content.find("{")
            end = content.rfind("}")
            if start == -1 or end == -1:
                return report
            localized = json.loads(content[start : end + 1])

        merged = {**report}
        for key in ["weekly_repos", "news_sections", "games", "topics", "observation"]:
            if key in localized:
                merged[key] = localized[key]
        report = merged
    except Exception as exc:
        print(f"[AI] 翻译整理失败，保留原内容: {exc}")
    for repo in report.get("weekly_repos", []):
        repo["description"] = translate_text_to_zh(repo.get("description", ""))
        if repo.get("recommendation"):
            repo["recommendation"] = translate_text_to_zh(repo.get("recommendation", ""))
    for section in report.get("news_sections", []):
        section["name"] = translate_text_to_zh(section.get("name", ""))
        for item in section.get("items", []):
            item["title"] = translate_text_to_zh(item.get("title", ""))
            item["summary"] = first_sentence(translate_text_to_zh(item.get("summary", "")))
    for item in report.get("games", []):
        item["title"] = translate_text_to_zh(item.get("title", ""))
        item["summary"] = first_sentence(translate_text_to_zh(item.get("summary", "")))
        item["platform"] = translate_text_to_zh(item.get("platform", ""))
    for topic in report.get("topics", []):
        topic["name"] = translate_text_to_zh(topic.get("name", ""))
        topic["summary"] = first_sentence(translate_text_to_zh(topic.get("summary", "")))
        for item in topic.get("items", []):
            item["title"] = translate_text_to_zh(item.get("title", ""))
            item["summary"] = first_sentence(translate_text_to_zh(item.get("summary", "")))
    report["observation"] = first_sentence(translate_text_to_zh(report.get("observation", "")))
    return report


def normalize_report_content(report: Dict, config: Dict) -> Dict:
    normalized = {**report}
    normalized["weekly_repos"] = curate_github_repos(
        normalized.get("weekly_repos", []),
        config.get("weekly_repo_count", GITHUB_REPO_MAX_ITEMS),
    )
    normalized_topics = []
    for topic in normalized.get("topics", [])[: config.get("max_topics", 4)]:
        topic_items = list(topic.get("items", []))[:TOPIC_ITEMS_MAX]
        normalized_topics.append({**topic, "items": topic_items})
    normalized["topics"] = normalized_topics
    return normalized


def build_entertainment_sections(
    edition: str,
    edition_settings: Dict,
    hotlist_candidates: List[Dict],
    entertainment_candidates: List[Dict],
    game_candidates: List[Dict],
) -> List[Dict]:
    used_keys: set[tuple[str, str]] = set()
    pure_social = dedupe_candidates(hotlist_candidates)
    all_candidates = dedupe_candidates(hotlist_candidates + entertainment_candidates + game_candidates)

    section_map = {
        "social": pick_entertainment_items(pure_social, "social", used_keys, min_items=3, max_items=8),
        "memes": pick_entertainment_items(pure_social, "memes", used_keys, min_items=3, max_items=6),
        "games": pick_entertainment_items(game_candidates + entertainment_candidates, "games", used_keys, min_items=3, max_items=6 if edition == "noon" else 8),
        "picks": pick_entertainment_items(all_candidates, "picks", used_keys, min_items=2, max_items=4),
        "video": pick_entertainment_items(all_candidates, "video", used_keys, min_items=3, max_items=8),
        "night_picks": pick_entertainment_items(all_candidates, "night_picks", used_keys, min_items=2, max_items=6),
    }

    sections = []
    for section in edition_settings.get("sections", []):
        sections.append(
            {
                "name": section["name"],
                "emoji": section.get("emoji", ""),
                "items": section_map.get(section["key"], []),
            }
        )
    return sections


def build_report(
    config: Dict,
    edition: str,
    today: datetime,
    candidates: List[Dict],
    news_candidates: Dict[str, List[Dict]],
    game_candidates: List[Dict],
    weekly_repos: List[Dict],
    weather: Dict,
) -> Dict:
    edition_settings = get_edition_settings(config, edition)
    if edition in {"noon", "evening"}:
        sections = build_entertainment_sections(
            edition,
            edition_settings,
            hotlist_candidates=candidates,
            entertainment_candidates=news_candidates.get("entertainment", []),
            game_candidates=game_candidates,
        )
        return build_edition_report(
            config=config,
            edition=edition,
            today=today,
            weather=weather if edition_settings.get("include_weather") else None,
            sections=sections,
            weekly_repos=[],
            observation=build_entertainment_observation(edition, sections),
        )

    curated = summarize_with_ai(config, candidates, news_candidates, game_candidates, weekly_repos, weather, today)
    report = {
        "edition": "morning",
        "title": build_issue_title(today.strftime("%Y-%m-%d"), edition="morning", template=edition_settings.get("title_template")),
        "datetime": today.strftime("%Y-%m-%d %H:%M"),
        "subtitle": curated.get("subtitle", edition_settings.get("subtitle", "为你整理的每日综合资讯精选")),
        "weather": weather,
        "weekly_repos": curated.get("weekly_repos", weekly_repos),
        "news_sections": curated.get("news_sections", fallback_news_sections(news_candidates, config.get("max_items_per_news_section", 5))),
        "games": curated.get("games", fallback_games(game_candidates, config.get("max_items_per_game_section", 5))),
        "topics": curated.get("topics", [])[: config["max_topics"]],
        "observation": curated.get("observation", "今天的看点主要集中在高质量技术源与中文社区热议的交汇处。"),
        "weekday": today.strftime("%A").lower(),
    }
    report = localize_report_content(report)
    report = normalize_report_content(report, config)
    report["body"] = render_issue_markdown(report)
    report["labels"] = edition_settings.get("labels", config.get("labels", ["daily-report", "morning"]))
    return report


def main() -> None:
    config = load_config()
    edition = os.environ.get("EDITION", "morning").strip().lower() or "morning"
    edition_settings = get_edition_settings(config, edition)
    timezone_name = config.get("timezone", "Asia/Shanghai")
    tz_now = get_now_in_timezone(timezone_name)
    weather = fetch_weather(config["city"], timezone_name=timezone_name) if edition_settings.get("include_weather", True) else {}
    trendradar_path = os.environ.get("TRENDRADAR_PATH", "trendradar-engine")
    rss_candidates = fetch_rss_candidates(config.get("english_feeds", []))
    hotlist_candidates = fetch_hotlist_candidates(config, trendradar_path)
    entertainment_candidates = fetch_rss_candidates(config.get("entertainment_feeds", []))
    domestic_news = fetch_news_section_candidates(config.get("news_feeds", {}).get("domestic", []), "domestic")
    international_news = fetch_news_section_candidates(config.get("news_feeds", {}).get("international", []), "international")
    game_news = fetch_game_news_candidates(config.get("game_news_feeds", []))
    game_releases = fetch_game_release_candidates(limit=max(config.get("max_items_per_game_section", GAME_MAX_ITEMS), GAME_MAX_ITEMS))
    candidates = dedupe_candidates(rss_candidates + hotlist_candidates)
    news_candidates = {
        "domestic": domestic_news,
        "international": international_news,
        "entertainment": entertainment_candidates,
    }
    game_candidates = curate_game_candidates(
        game_releases,
        game_news,
        limit=max(config.get("max_items_per_game_section", GAME_MAX_ITEMS), GAME_MAX_ITEMS),
    )
    weekly_repos = []
    try:
        repo_candidates = fetch_github_trending(period="daily", limit=max(config.get("weekly_repo_count", GITHUB_REPO_MAX_ITEMS), GITHUB_REPO_MAX_ITEMS))
        weekly_repos = curate_github_repos(repo_candidates, config.get("weekly_repo_count", GITHUB_REPO_MAX_ITEMS))
    except Exception as exc:
        print(f"[GitHub Trending] 抓取失败，跳过该板块: {exc}")

    report = build_report(config, edition, tz_now, hotlist_candidates if edition in {"noon", "evening"} else candidates, news_candidates, game_candidates, weekly_repos, weather)

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
