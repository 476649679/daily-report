import unittest

from scripts.generate_report import mix_game_candidates, normalize_model_name, parse_steam_release_calendar_html


class GenerateReportTests(unittest.TestCase):
    def test_normalize_model_name_strips_provider_prefix_for_raw_openai_endpoint(self):
        self.assertEqual(normalize_model_name("openai/LongCat-Flash-Chat"), "LongCat-Flash-Chat")
        self.assertEqual(normalize_model_name("LongCat-Flash-Chat"), "LongCat-Flash-Chat")
        self.assertEqual(normalize_model_name("deepseek/deepseek-chat"), "deepseek-chat")

    def test_parse_steam_release_calendar_html_extracts_games(self):
        html = """
        <html>
          <body>
            <a href="/app/111">First Game</a>
            <a href="/app/222">Second Game</a>
            <a href="/app/333">Third Game</a>
          </body>
        </html>
        """

        items = parse_steam_release_calendar_html(html, limit=2)

        self.assertEqual(
            items,
            [
                {
                    "source": "Steam 发售日历",
                    "source_type": "game_release",
                    "title": "First Game",
                    "url": "https://stmstat.com/app/111",
                    "summary": "Steam 发售日历中的新近上架作品，可结合新闻热度判断是否值得关注。",
                    "platform": "Steam",
                    "release_date": "待确认",
                },
                {
                    "source": "Steam 发售日历",
                    "source_type": "game_release",
                    "title": "Second Game",
                    "url": "https://stmstat.com/app/222",
                    "summary": "Steam 发售日历中的新近上架作品，可结合新闻热度判断是否值得关注。",
                    "platform": "Steam",
                    "release_date": "待确认",
                },
            ],
        )

    def test_mix_game_candidates_interleaves_release_and_news_items(self):
        releases = [
            {"title": "Release 1", "source_type": "game_release"},
            {"title": "Release 2", "source_type": "game_release"},
            {"title": "Release 3", "source_type": "game_release"},
        ]
        news = [
            {"title": "News 1", "source_type": "game_news"},
            {"title": "News 2", "source_type": "game_news"},
        ]

        items = mix_game_candidates(releases, news, limit=5)

        self.assertEqual(
            [item["title"] for item in items],
            ["Release 1", "News 1", "Release 2", "News 2", "Release 3"],
        )


if __name__ == "__main__":
    unittest.main()
