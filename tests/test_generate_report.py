import unittest

from scripts.generate_report import normalize_model_name


class GenerateReportTests(unittest.TestCase):
    def test_normalize_model_name_strips_provider_prefix_for_raw_openai_endpoint(self):
        self.assertEqual(normalize_model_name("openai/LongCat-Flash-Chat"), "LongCat-Flash-Chat")
        self.assertEqual(normalize_model_name("LongCat-Flash-Chat"), "LongCat-Flash-Chat")
        self.assertEqual(normalize_model_name("deepseek/deepseek-chat"), "deepseek-chat")


if __name__ == "__main__":
    unittest.main()
