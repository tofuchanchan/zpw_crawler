import tempfile
import unittest
from pathlib import Path

from src.zpw_crawler.config import job_from_url
from src.zpw_crawler.fetcher import FetchResponse
from src.zpw_crawler.runner import run_jobs


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
    <div class="pages"><cite>共1条/1页</cite></div>
  </body>
</html>
"""

DETAIL_HTML = """
<html>
  <head><title>武汉演示贸易有限公司</title></head>
  <body>
    <h1>武汉演示贸易有限公司</h1>
    <h4>专注合金贸易</h4>
    <div class="main_body"><h2>公司介绍</h2><p>公开介绍。</p></div>
    <div>访问量:99</div>
  </body>
</html>
"""


class FakeFetcher:
    def fetch(self, url, delay=None):
        if "company/search.php" in url:
            return FetchResponse(url=url, text=SEARCH_HTML, status_code=200)
        return FetchResponse(url=url, text=DETAIL_HTML, status_code=200)


class RunnerTest(unittest.TestCase):
    def test_run_jobs_exports_excel(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            job = job_from_url(
                "http://www.027zpw.com/company/search.php?kw=%E8%B4%B8%E6%98%93&size=1",
                max_pages=1,
                output_name="demo.xlsx",
            )
            results = run_jobs(
                [job],
                output_dir=tmp_path / "outputs",
                cache_dir=tmp_path / "cache",
                fetcher=FakeFetcher(),
            )
            self.assertEqual(len(results), 1)
            self.assertTrue((tmp_path / "outputs" / "demo.xlsx").exists())
            self.assertEqual(results[0].companies[0]["homepage_status"], "success")


if __name__ == "__main__":
    unittest.main()
