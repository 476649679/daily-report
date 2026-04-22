import unittest
from unittest.mock import patch, Mock

from scripts.generate_report import localize_report_content, summarize_with_ai
from scripts.report_builder import build_issue_title, render_issue_markdown


class ReportBuilderTests(unittest.TestCase):
    def test_render_issue_markdown_includes_github_repo_section_daily(self):
        report = {
            "title": "个人资讯简报 | 2026-04-20 早间",
            "datetime": "2026-04-20 08:00",
            "subtitle": "每日精选",
            "weather": {
                "city": "韶关",
                "summary": "晴",
                "temperature": "23°C",
                "advice": "适合轻薄春装",
                "apparent_temperature": "23°C",
                "humidity": "64%",
                "wind_speed": "11 km/h",
                "tomorrow": {
                    "date": "4月21日",
                    "temperature_range": "20°C - 28°C",
                    "summary": "多云",
                    "advice": "早晚温差较大，建议带一件薄外套",
                },
            },
            "weekly_repos": [
                {
                    "rank": 1,
                    "name": "owner/repo",
                    "url": "https://github.com/owner/repo",
                    "description": "一个实用仓库",
                    "stars": "12.3k",
                    "today_stars": "1.2k",
                    "language": "Python",
                    "recommendation": "适合自动化日报和数据清洗场景。",
                }
            ],
            "news_sections": [
                {
                    "name": "国内新闻",
                    "emoji": "🇨🇳",
                    "items": [
                        {"title": f"国内新闻{i}", "url": f"https://example.com/cn{i}", "summary": f"国内摘要{i}"}
                        for i in range(1, 7)
                    ],
                },
                {
                    "name": "国际新闻",
                    "emoji": "🌍",
                    "items": [
                        {"title": f"国际新闻{i}", "url": f"https://example.com/world{i}", "summary": f"国际摘要{i}"}
                        for i in range(1, 7)
                    ],
                },
            ],
            "games": [
                {
                    "title": f"游戏{i}",
                    "url": f"https://example.com/game{i}",
                    "summary": f"游戏摘要{i}",
                    "platform": "Steam",
                    "release_date": "2026-04-20",
                }
                for i in range(1, 7)
            ],
            "topics": [
                {
                    "name": "AI 模型动态",
                    "summary": "关注模型更新。",
                    "items": [
                        {"title": "Claude 新版本", "url": "https://example.com/1", "summary": "新版重点强化多步推理和代理协作。"},
                        {"title": "GPT 新能力", "url": "https://example.com/2", "summary": "更适合低延迟开发场景。"},
                        {"title": "Gemini 更新", "url": "https://example.com/3", "summary": "移动端离线推理能力继续提升。"},
                        {"title": "不应出现", "url": "https://example.com/4"},
                    ],
                }
            ],
            "observation": "今天重点是模型与工具。",
            "weekday": "tuesday",
        }

        content = render_issue_markdown(report)

        self.assertIn("## 🔥 GitHub 仓库热榜推荐", content)
        self.assertIn("1. **[owner/repo](https://github.com/owner/repo)**", content)
        self.assertIn("⭐ 今日新增 1.2k | ⭐ 总 Star 12.3k | Python", content)
        self.assertIn("一个实用仓库", content)
        self.assertIn("适合自动化日报和数据清洗场景。", content)
        self.assertIn("### 今日天气", content)
        self.assertIn("### 明日预报（4月21日）", content)
        self.assertIn("## 📰 新闻资讯", content)
        self.assertIn("### 🇨🇳 国内新闻", content)
        self.assertIn("### 🌍 国际新闻", content)
        self.assertIn("**[国内新闻1](https://example.com/cn1)**", content)
        self.assertIn("国内摘要1", content)
        self.assertIn("国内新闻6", content)
        self.assertIn("## 🎮 近期游戏", content)
        self.assertIn("**[游戏1](https://example.com/game1)**", content)
        self.assertIn("平台: Steam", content)
        self.assertIn("游戏6", content)
        self.assertIn("### AI 模型动态", content)
        self.assertIn("**[Claude 新版本](https://example.com/1)**", content)
        self.assertIn("新版重点强化多步推理和代理协作。", content)
        self.assertNotIn("链接: https://example.com/1", content)
        self.assertIn("**[不应出现](https://example.com/4)**", content)

    def test_render_issue_markdown_skips_github_repo_section_when_no_repos(self):
        report = {
            "title": "个人资讯简报 | 2026-04-21 早间",
            "datetime": "2026-04-21 08:00",
            "subtitle": "每日精选",
            "weather": {
                "city": "韶关",
                "summary": "多云",
                "temperature": "22°C",
                "advice": "体感舒适",
            },
            "weekly_repos": [],
            "topics": [],
            "observation": "平稳。",
            "weekday": "tuesday",
        }

        content = render_issue_markdown(report)

        self.assertNotIn("GitHub 仓库热榜推荐", content)
        self.assertIn("## 🌤️ 天气", content)

    def test_build_issue_title_matches_morning_template(self):
        self.assertEqual(
            build_issue_title("2026-04-20"),
            "个人资讯简报 | 2026-04-20 早间",
        )

    def test_build_issue_title_supports_noon_and_evening_templates(self):
        self.assertEqual(
            build_issue_title("2026-04-20", edition="noon"),
            "午间轻松报 | 2026-04-20",
        )
        self.assertEqual(
            build_issue_title("2026-04-20", edition="evening"),
            "夜间玩乐报 | 2026-04-20",
        )

    def test_render_issue_markdown_uses_noon_entertainment_layout_without_weather(self):
        report = {
            "edition": "noon",
            "title": "午间轻松报 | 2026-04-20",
            "datetime": "2026-04-20 12:00",
            "subtitle": "中午适合快速刷一遍的娱乐休闲精选",
            "weekly_repos": [],
            "sections": [
                {
                    "name": "社媒热议",
                    "emoji": "📱",
                    "items": [
                        {
                            "title": "微博热议话题",
                            "url": "https://example.com/social",
                            "summary": "这条话题在多个平台持续发酵，适合中午快速跟进。",
                        }
                    ],
                },
                {
                    "name": "今日热梗",
                    "emoji": "🤣",
                    "items": [
                        {
                            "title": "爆梗名场面",
                            "url": "https://example.com/meme",
                            "summary": "今天讨论度最高的梗图和二创集中在这条线上。",
                        }
                    ],
                },
            ],
            "observation": "今天中午的讨论明显偏社媒热梗和视频平台扩散。",
        }

        content = render_issue_markdown(report)

        self.assertNotIn("## 🌤️ 天气", content)
        self.assertIn("## 📱 社媒热议", content)
        self.assertIn("## 🤣 今日热梗", content)
        self.assertIn("**[微博热议话题](https://example.com/social)**", content)
        self.assertIn("## 💡 午间观察", content)

    def test_render_issue_markdown_uses_evening_entertainment_layout(self):
        report = {
            "edition": "evening",
            "title": "夜间玩乐报 | 2026-04-20",
            "datetime": "2026-04-20 21:00",
            "subtitle": "今晚值得看的轻松内容和热门游戏动向",
            "weekly_repos": [],
            "sections": [
                {
                    "name": "晚间游戏热点",
                    "emoji": "🎮",
                    "items": [
                        {
                            "title": "GTA 6 新预告",
                            "url": "https://example.com/game",
                            "summary": "这是今晚最值得点进去看的大型游戏热点。",
                            "meta": "来源：Google News 游戏",
                        }
                    ],
                },
                {
                    "name": "今夜玩点啥",
                    "emoji": "🌙",
                    "items": [
                        {
                            "title": "今晚适合补完的内容",
                            "url": "https://example.com/night",
                            "summary": "如果只想睡前轻松刷一条，这条最合适。",
                        }
                    ],
                },
            ],
            "observation": "今晚的关注点明显集中在大型游戏和视频平台延续热度上。",
        }

        content = render_issue_markdown(report)

        self.assertNotIn("## 🌤️ 天气", content)
        self.assertIn("## 🎮 晚间游戏热点", content)
        self.assertIn("## 🌙 今夜玩点啥", content)
        self.assertIn("来源：Google News 游戏", content)
        self.assertIn("## 💡 夜间观察", content)

    @patch("scripts.generate_report.requests.post")
    def test_summarize_with_ai_falls_back_when_ai_request_fails(self, mock_post):
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = Exception("bad request")
        mock_post.return_value = mock_response

        with patch.dict(
            "os.environ",
            {
                "AI_API_KEY": "x",
                "AI_MODEL": "test-model",
                "AI_API_BASE": "https://example.com",
            },
            clear=False,
        ):
            result = summarize_with_ai(
                {"max_topics": 3, "max_items_per_topic": 3},
                [
                    {
                        "source": "知乎",
                        "title": "测试标题",
                        "url": "https://example.com/1",
                        "summary": "",
                    }
                ],
                {"domestic": [], "international": []},
                [],
                [],
                {"city": "韶关"},
                __import__("datetime").datetime(2026, 4, 20, 8, 0, 0),
            )

        self.assertIn("topics", result)
        self.assertTrue(result["topics"])

    @patch("scripts.generate_report.requests.post")
    def test_localize_report_content_translates_english_fields(self, mock_post):
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": """{
                          "weekly_repos": [{"name":"owner/repo","url":"https://github.com/owner/repo","description":"一个高效编程仓库","stars":"1k","today_stars":"100","language":"Python","rank":1,"recommendation":"适合开发者关注。"}],
                          "news_sections": [{"name":"国际新闻","emoji":"🌍","items":[{"title":"重大国际新闻","url":"https://example.com/world","summary":"国际局势出现重要变化。"}]}],
                          "games": [{"title":"热门新游","url":"https://example.com/game","summary":"这是一款值得关注的新作。","platform":"多平台","release_date":"新闻更新"}],
                          "topics": [{"name":"AI动态","summary":"模型更新密集出现。","items":[{"title":"新模型发布","url":"https://example.com/ai","summary":"新模型聚焦推理与效率。"}]}],
                          "observation": "今天的重点集中在国际局势和AI工具更新。"
                        }"""
                    }
                }
            ]
        }
        mock_post.return_value = mock_response

        report = {
            "weekly_repos": [{"name": "owner/repo", "url": "https://github.com/owner/repo", "description": "A useful coding repo", "stars": "1k", "today_stars": "100", "language": "Python", "rank": 1}],
            "news_sections": [{"name": "国际新闻", "emoji": "🌍", "items": [{"title": "Big world news", "url": "https://example.com/world", "summary": "A long english summary."}]}],
            "games": [{"title": "Hot new game", "url": "https://example.com/game", "summary": "An exciting new title.", "platform": "Multi-platform", "release_date": "News"}],
            "topics": [{"name": "AI", "summary": "English summary", "items": [{"title": "New model", "url": "https://example.com/ai", "summary": "English item summary"}]}],
            "observation": "English observation",
        }

        with patch.dict(
            "os.environ",
            {
                "AI_API_KEY": "x",
                "AI_MODEL": "openai/LongCat-Flash-Chat",
                "AI_API_BASE": "https://example.com/openai/v1",
            },
            clear=False,
        ):
            localized = localize_report_content(report)

        self.assertEqual(localized["weekly_repos"][0]["description"], "一个高效编程仓库")
        self.assertEqual(localized["news_sections"][0]["items"][0]["summary"], "国际局势出现重要变化。")
        self.assertEqual(localized["games"][0]["summary"], "这是一款值得关注的新作。")
        self.assertEqual(localized["topics"][0]["items"][0]["summary"], "新模型聚焦推理与效率。")
        self.assertEqual(localized["observation"], "今天的重点集中在国际局势和AI工具更新。")


if __name__ == "__main__":
    unittest.main()
