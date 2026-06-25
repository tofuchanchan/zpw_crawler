# 027zpw 企业采集器

一个面向 `http://www.027zpw.com/company/search.php` 的公开企业搜索采集 MVP。

它支持粘贴搜索 URL 或使用 YAML 批量配置，抓取搜索结果分页，按需进入企业公开主页补充详情，并导出 Excel。

## 功能

- 解析完整搜索 URL
- 支持 YAML 多任务配置
- 抓取搜索结果分页
- 解析企业名称、主页、简介、主营产品、经营类型、核实状态、列表地址、电话
- 可选抓取企业公开主页详情和 `公司档案`
- 公司档案字段包含公司类型、所在地、公司规模、注册资本、注册年份、资料认证、保证金、经营模式、经营范围、销售产品、主营行业等
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

首次运行前需要配置登录账号。密码不会明文保存，先生成密码哈希：

```powershell
.venv\Scripts\python.exe scripts\create_password_hash.py --username admin
```

把输出内容写入本机文件 `.streamlit/secrets.toml`：

```toml
[auth.users]
admin = "脚本输出的 pbkdf2_sha256 哈希"
```

`.streamlit/secrets.toml` 已加入 `.gitignore`，不要提交到 GitHub。也可以用环境变量配置账号：

```powershell
$env:ZPW_AUTH_USERS_JSON='{"admin":"脚本输出的 pbkdf2_sha256 哈希"}'
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
4. Advanced settings 里 Python version 建议选择 `3.11`。
5. Python 依赖会从 `requirements.txt` 安装。
6. 部署完成后得到公网访问地址。

如果页面提示 `Error installing requirements`：

1. 点击 Streamlit Cloud 里的 `Manage App`。
2. 打开日志终端，确认失败发生在依赖安装阶段。
3. 进入 `Settings` / `Advanced settings`，把 Python version 改成 `3.11`。
4. 点击 `Reboot app` 或重新部署。

这个方案适合 MVP 和小批量任务。全量抓取并开启详情时，任务会比较久，建议先用 `max_pages=1` 或 `max_pages=3` 验证字段。

## 本地运行并给外部访问

如果 Streamlit Cloud 无法连接 `www.027zpw.com`，可以把应用跑在本机，再用公网隧道让别人访问。

先启动本地 Streamlit：

```powershell
cd "C:\Users\fuweicheng\PycharmProjects\pythonProject\需求项目集\波兰VAT移仓算法\027zpw_company_crawler"
.venv\Scripts\streamlit.exe run app.py --server.address 127.0.0.1 --server.port 8501
```

再开一个 PowerShell，用 Cloudflare Tunnel 暴露本地端口：

```powershell
cloudflared tunnel --url http://127.0.0.1:8501
```

命令会输出一个公网 `https://*.trycloudflare.com` 地址。把这个地址和登录账号发给使用者即可。

注意：

- 本机必须保持开机，两个命令窗口都不要关闭。
- Quick Tunnel 地址可能变化，适合演示和临时使用。
- 长期稳定使用建议配置 Cloudflare Named Tunnel 或部署到一台能访问目标站的服务器。
- 登录账号必须配置强密码，不要复用个人常用密码。

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
