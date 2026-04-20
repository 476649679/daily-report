import unittest
from unittest.mock import Mock, patch

from scripts.generate_report import (
    curate_game_candidates,
    curate_news_candidates,
    is_excluded_game_candidate,
    mix_game_candidates,
    normalize_model_name,
    parse_steam_release_calendar_html,
    translate_text_to_zh,
)


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

    def test_is_excluded_game_candidate_filters_adult_or_low_signal_entries(self):
        self.assertTrue(is_excluded_game_candidate({"title": "Sisters in Sin 🔞", "summary": ""}))
        self.assertTrue(is_excluded_game_candidate({"title": "Great Game Soundtrack", "summary": ""}))
        self.assertFalse(is_excluded_game_candidate({"title": "Draw Steel", "summary": "Tactical fantasy RPG"}))

    def test_curate_game_candidates_prefers_high_signal_items(self):
        releases = [
            {"title": "Sisters in Sin 🔞", "source_type": "game_release", "summary": "", "source": "Steam 发售日历"},
            {"title": "Draw Steel", "source_type": "game_release", "summary": "", "source": "Steam 发售日历"},
            {"title": "MELFIAS", "source_type": "game_release", "summary": "", "source": "Steam 发售日历"},
        ]
        news = [
            {"title": "Pragmata Review", "source_type": "game_news", "summary": "Capcom 新作评测", "source": "Game Informer"},
            {"title": "Bloodborne Movie News", "source_type": "game_news", "summary": "影视化动态", "source": "Game Informer"},
        ]

        items = curate_game_candidates(releases, news, limit=4)

        self.assertEqual(
            [item["title"] for item in items],
            ["Pragmata Review", "Draw Steel", "Bloodborne Movie News", "MELFIAS"],
        )

    def test_curate_news_candidates_prefers_major_and_recent_news(self):
        items = [
            {
                "title": "全民阅读活动在银川举行",
                "summary": "地方活动新闻",
                "source": "Google News 国内",
                "published_at": "2026-04-20T08:00:00",
            },
            {
                "title": "国际油价上涨 伊朗相关局势引发市场波动",
                "summary": "能源与地缘政治风险升温",
                "source": "BBC World",
                "published_at": "2026-04-20T09:00:00",
            },
            {
                "title": "乌克兰警方负责人辞职 涉致命枪击事件调查",
                "summary": "安全与政府问责受关注",
                "source": "BBC World",
                "published_at": "2026-04-20T07:00:00",
            },
            {
                "title": "特朗普称扣押伊朗船只后 油价继续上涨",
                "summary": "国际市场出现剧烈波动",
                "source": "Google News 国际",
                "published_at": "2026-04-20T10:00:00",
            },
        ]

        curated = curate_news_candidates(items, limit=3, section="international")

        self.assertEqual(
            [item["title"] for item in curated],
            [
                "特朗普称扣押伊朗船只后 油价继续上涨",
                "国际油价上涨 伊朗相关局势引发市场波动",
                "乌克兰警方负责人辞职 涉致命枪击事件调查",
            ],
        )

    def test_curate_news_candidates_trims_summary_to_one_sentence(self):
        items = [
            {
                "title": "重大国际新闻",
                "summary": "第一句很重要。第二句不应该保留。第三句更不应该保留。",
                "source": "BBC World",
                "published_at": "2026-04-20T10:00:00",
            }
        ]

        curated = curate_news_candidates(items, limit=1, section="international")

        self.assertEqual(curated[0]["summary"], "第一句很重要。")

    def test_curate_news_candidates_respects_domestic_section(self):
        items = [
            {
                "title": "日本三陆近海地区发生7.5级地震",
                "summary": "日本强震引发海啸预警。",
                "source": "中新网滚动",
                "published_at": "2026-04-20T10:00:00",
            },
            {
                "title": "国务院部署稳外贸稳就业重点工作",
                "summary": "多项政策同步推进。",
                "source": "Google News 国内",
                "published_at": "2026-04-20T09:00:00",
            },
        ]

        curated = curate_news_candidates(items, limit=2, section="domestic")

        self.assertEqual([item["title"] for item in curated], ["国务院部署稳外贸稳就业重点工作"])

    @patch("scripts.generate_report.requests.get")
    def test_translate_text_to_zh_uses_google_translate_fallback(self, mock_get):
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = [[["这是一个测试", "This is a test", None, None]]]
        mock_get.return_value = mock_response

        translated = translate_text_to_zh("This is a test")

        self.assertEqual(translated, "这是一个测试")


if __name__ == "__main__":
    unittest.main()
