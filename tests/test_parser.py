import unittest
from datetime import datetime

from src.zpw_crawler.parser import parse_company_homepage, parse_search_page, parse_total_counts


SEARCH_HTML = """
<html>
  <body>
    <ul>
      <li class="offer paGetId">
        <h2><a class="Title" href="/index.php?homepage=demo01">武汉演示贸易有限公司</a></h2>
        <div class="Biz-type">企业简介文本</div>
        <div class="sw-mod-allcompany-Service">主营：合金、贸易</div>
        <div class="iconCollection">贸易商 [未核实]</div>
      </li>
    </ul>
    <div class="pages"><cite>共1765条/89页</cite></div>
  </body>
</html>
"""


DETAIL_HTML = """
<html>
  <head>
    <title>武汉演示贸易有限公司</title>
    <meta name="keywords" content="贸易,合金">
    <meta name="description" content="公开主页描述">
  </head>
  <body>
    <h1>武汉演示贸易有限公司</h1>
    <h4>专注合金贸易</h4>
    <div class="main_body">
      <h2>公司介绍</h2>
      <p>这里是公开公司介绍。</p>
      <img src="/skin/demo.jpg">
    </div>
    <div>访问量:1234</div>
  </body>
</html>
"""


class ParserTest(unittest.TestCase):
    def test_parse_total_counts(self):
        self.assertEqual(parse_total_counts(SEARCH_HTML), (1765, 89))

    def test_parse_search_page(self):
        rows = parse_search_page(
            SEARCH_HTML,
            job_name="demo",
            keyword="贸易",
            page=1,
            source_url="http://www.027zpw.com/company/search.php?page=1",
            fetched_at=datetime(2026, 6, 25, 10, 0, 0),
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["company_name"], "武汉演示贸易有限公司")
        self.assertEqual(rows[0]["username"], "demo01")
        self.assertEqual(rows[0]["verified_status"], "未核实")

    def test_parse_company_homepage(self):
        detail = parse_company_homepage(
            DETAIL_HTML,
            page_url="http://www.027zpw.com/index.php?homepage=demo01",
        )
        self.assertEqual(detail["homepage_status"], "success")
        self.assertEqual(detail["detail_slogan"], "专注合金贸易")
        self.assertEqual(detail["visit_count"], "1234")
        self.assertEqual(detail["company_image_url"], "http://www.027zpw.com/skin/demo.jpg")


if __name__ == "__main__":
    unittest.main()
