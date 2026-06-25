# 027zpw 企业采集器

一个面向 `http://www.027zpw.com/company/search.php` 的公开企业搜索采集 MVP。

它支持粘贴搜索 URL 或使用 YAML 批量配置，抓取搜索结果分页，按需进入企业公开主页补充详情，并导出 Excel。

## 功能

- 解析完整搜索 URL
- 支持 YAML 多任务配置
- 抓取搜索结果分页
- 解析企业名称、主页、简介、主营产品、经营类型、核实状态
- 可选抓取企业公开主页详情
- 按 `username` / `homepage_url` / `company_name + main_products` 去重
- SQLite 缓存用于断点续跑
- 导出 Excel，包含 `companies`、`failed_urls`、`run_log`、`raw_conditions`
- Streamlit Web 页面，可部署成公网访问应用

## 本地运行

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

命令行运行：

```bash
python crawl_027zpw_companies.py --url "http://www.027zpw.com/company/search.php?kw=%E8%B4%B8%E6%98%93&vip=0&type=0&catid=0&mode=0&areaid=0&size=1" --max-pages 1
```

YAML 批量任务：

```bash
python crawl_027zpw_companies.py --config configs/027zpw_jobs.example.yml
```

## 部署到 Streamlit Community Cloud

1. 打开 Streamlit Community Cloud。
2. 选择 GitHub 仓库 `tofuchanchan/zpw_crawler`。
3. Main file path 填写 `app.py`。
4. Python 依赖会从 `requirements.txt` 安装。
5. 部署完成后得到公网访问地址。

这个方案适合 MVP 和小批量任务。全量抓取并开启详情时，任务会比较久，建议先用 `max_pages=1` 或 `max_pages=3` 验证字段。

## 部署到 Render

如果要跑更久的任务，Render Web Service 更合适：

- Build Command: `pip install -r requirements.txt`
- Start Command: `streamlit run app.py --server.port $PORT --server.address 0.0.0.0`

全量采集如果要长期稳定运行，建议后续升级为 `FastAPI + Worker + 队列 + 数据库`。MVP 先别硬上企业级架构，杀鸡别搬火箭筒，丢人。

## 合规边界

- 只采集公开搜索页和公开企业主页
- 不访问 `/member/`
- 不绕过登录、会员权限、验证码或接口限制
- 不采集无权限查看的联系方式
- 默认低频请求，避免高并发冲站点
