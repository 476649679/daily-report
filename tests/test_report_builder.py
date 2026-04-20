import unittest

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
            "topics": [
                {
                    "name": "AI 模型动态",
                    "summary": "关注模型更新。",
                    "items": [
                        {"title": "Claude 新版本", "url": "https://example.com/1"},
                        {"title": "GPT 新能力", "url": "https://example.com/2"},
                        {"title": "Gemini 更新", "url": "https://example.com/3"},
                        {"title": "不应出现", "url": "https://example.com/4"},
                    ],
                }
            ],
            "observation": "今天重点是模型与工具。",
            "weekday": "monday",
        }

        content = render_issue_markdown(report)

        self.assertIn("## 🔥 GitHub 仓库热榜推荐", content)
        self.assertIn("1. [owner/repo](https://github.com/owner/repo)", content)
        self.assertIn("Stars：`12.3k`", content)
        self.assertIn("### AI 模型动态", content)
        self.assertIn("[Claude 新版本](https://example.com/1)", content)
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
        self.assertIn("## 🌤️ 韶关天气", content)

    def test_build_issue_title_matches_morning_template(self):
        self.assertEqual(
            build_issue_title("2026-04-20"),
            "个人资讯简报 | 2026-04-20 早间",
        )


if __name__ == "__main__":
    unittest.main()
