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
        <div class="Address"><em>地址：</em>辽宁省大连市保税区东北六街</div>
        <div class="Address"><em>电话：</em>0411-66776939 </div>
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
    <div class="main_head"><div><strong>公司档案</strong></div></div>
    <div class="main_body">
      <table>
        <tr>
          <td class="f_b">公司名称：</td><td>武汉演示贸易有限公司</td>
          <td class="f_b">公司类型：</td><td>个体经营 (贸易商)</td>
        </tr>
        <tr>
          <td class="f_b">所 在 地：</td><td>辽宁/大连市</td>
          <td class="f_b">公司规模：</td><td>1-49人</td>
        </tr>
        <tr>
          <td class="f_b">注册资本：</td><td>50万人民币</td>
          <td class="f_b">注册年份：</td><td>2018</td>
        </tr>
        <tr><td class="f_b">资料认证：</td><td><img title="资料通过工商认证"></td></tr>
        <tr><td class="f_b">保 证 金：</td><td>已缴纳 0.00 元</td></tr>
        <tr><td class="f_b">经营模式：</td><td>贸易商</td></tr>
        <tr><td class="f_b">经营范围：</td><td>数控刀具，机械附件</td></tr>
        <tr><td class="f_b">销售的产品：</td><td>数控刀具</td></tr>
        <tr>
          <td class="f_b">主营行业：</td>
          <td>
            <table>
              <tr><td>机械/设备/模具 / 刀具、夹具 / 刀片</td></tr>
              <tr><td>机械/设备/模具 / 刀具、夹具 / 钻头</td></tr>
            </table>
          </td>
        </tr>
      </table>
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
        self.assertEqual(rows[0]["list_address"], "辽宁省大连市保税区东北六街")
        self.assertEqual(rows[0]["phone"], "0411-66776939")

    def test_parse_company_homepage(self):
        detail = parse_company_homepage(
            DETAIL_HTML,
            page_url="http://www.027zpw.com/index.php?homepage=demo01",
        )
        self.assertEqual(detail["homepage_status"], "success")
        self.assertEqual(detail["detail_slogan"], "专注合金贸易")
        self.assertEqual(detail["visit_count"], "1234")
        self.assertEqual(detail["company_image_url"], "http://www.027zpw.com/skin/demo.jpg")
        self.assertEqual(detail["profile_company_name"], "武汉演示贸易有限公司")
        self.assertEqual(detail["profile_company_type"], "个体经营 (贸易商)")
        self.assertEqual(detail["profile_location"], "辽宁/大连市")
        self.assertEqual(detail["profile_company_size"], "1-49人")
        self.assertEqual(detail["profile_registered_capital"], "50万人民币")
        self.assertEqual(detail["profile_registered_year"], "2018")
        self.assertEqual(detail["profile_data_certification"], "资料通过工商认证")
        self.assertEqual(detail["profile_security_deposit"], "已缴纳 0.00 元")
        self.assertEqual(detail["profile_business_model"], "贸易商")
        self.assertEqual(detail["profile_business_scope"], "数控刀具，机械附件")
        self.assertEqual(detail["profile_selling_products"], "数控刀具")
        self.assertEqual(
            detail["profile_main_industries"],
            "机械/设备/模具 / 刀具、夹具 / 刀片 | 机械/设备/模具 / 刀具、夹具 / 钻头",
        )


if __name__ == "__main__":
    unittest.main()
