import unittest

from scripts.fetch_github_trending import parse_github_trending_html


class FetchGithubTrendingTests(unittest.TestCase):
    def test_parse_github_trending_html_extracts_rank_name_description_and_stars(self):
        html = """
        <article class="Box-row">
          <h2><a href="/owner/repo"> owner / repo </a></h2>
          <p>Useful project</p>
          <span itemprop="programmingLanguage">Python</span>
          <a href="/owner/repo/stargazers">12,345</a>
          <span>1,234 stars this week</span>
        </article>
        <article class="Box-row">
          <h2><a href="/another/tool"> another / tool </a></h2>
          <p>Another tool</p>
          <a href="/another/tool/stargazers">9,001</a>
        </article>
        """

        repos = parse_github_trending_html(html, limit=5)

        self.assertEqual(len(repos), 2)
        self.assertEqual(repos[0]["rank"], 1)
        self.assertEqual(repos[0]["name"], "owner/repo")
        self.assertEqual(repos[0]["url"], "https://github.com/owner/repo")
        self.assertEqual(repos[0]["description"], "Useful project")
        self.assertEqual(repos[0]["stars"], "12.3k")
        self.assertEqual(repos[0]["today_stars"], "1.2k")
        self.assertEqual(repos[0]["language"], "Python")


if __name__ == "__main__":
    unittest.main()
