import unittest
from unittest.mock import patch, Mock

from scripts.generate_report import summarize_with_ai
from scripts.report_builder import build_issue_title, render_issue_markdown


class ReportBuilderTests(unittest.TestCase):
    def test_render_issue_markdown_includes_weekly_repo_section_on_monday(self):
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
            "weekday": "monday",
        }

        content = render_issue_markdown(report)

        self.assertIn("## 🔥 GitHub 仓库热榜推荐", content)
        self.assertIn("1. **[owner/repo](https://github.com/owner/repo)**", content)
        self.assertIn("⭐ 今日新增 1.2k | ⭐ 总 Star 12.3k | Python", content)
        self.assertIn("一个实用仓库", content)
        self.assertIn("适合自动化日报和数据清洗场景。", content)
        self.assertIn("### 今日天气", content)
        self.assertIn("### 明日预报（4月21日）", content)
        self.assertIn("### AI 模型动态", content)
        self.assertIn("**[Claude 新版本](https://example.com/1)**", content)
        self.assertIn("新版重点强化多步推理和代理协作。", content)
        self.assertNotIn("链接: https://example.com/1", content)
        self.assertNotIn("不应出现", content)

    def test_render_issue_markdown_skips_weekly_repo_section_when_not_monday(self):
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
            "weekly_repos": [
                {
                    "rank": 1,
                    "name": "owner/repo",
                    "url": "https://github.com/owner/repo",
                    "description": "A useful repo",
                    "stars": "12.3k",
                }
            ],
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
                [],
                {"city": "韶关"},
                __import__("datetime").datetime(2026, 4, 20, 8, 0, 0),
            )

        self.assertIn("topics", result)
        self.assertTrue(result["topics"])


if __name__ == "__main__":
    unittest.main()
