# 027zpw 企业搜索增强版采集方案

## 1. 目标

批量采集 `http://www.027zpw.com/company/search.php` 企业搜索结果，并导出 Excel。

增强版目标不是只把搜索页列表扒下来就完事，而是：

- 支持用户自定义搜索条件；
- 批量抓取搜索结果分页；
- 进入企业公开主页补充详情字段；
- 自动去重、断点续跑、失败重试；
- 输出结构化 Excel，方便筛选、清洗和二次处理。

当前样例 URL 的搜索结果页显示：`共1765条 / 89页`。页面为服务端渲染 HTML，适合用 `requests + BeautifulSoup/lxml + pandas/openpyxl` 实现，不需要浏览器自动化。

## 2. 合规边界

已检查目标站 `robots.txt`：

- 未禁止 `/company/search.php`；
- 未禁止公开企业主页 `/index.php?homepage=...`；
- 禁止 `/member/`；
- 联系方式页示例返回“您所在的会员组无权查看联系方式”。

采集边界：

- 只采集公开搜索页和公开企业主页；
- 不访问 `/member/`；
- 不绕过登录、会员权限、验证码或接口限制；
- 不采集无权限查看的联系方式；
- 请求间隔默认 `1.5-3.0 秒`，不做高并发硬冲。

说白了：能从前台公开页面看到的就拿，权限墙后面的别碰。别把数据采集写成网络版撬门，没必要，也不体面。

## 3. 支持的搜索条件

### 3.1 URL 参数模型

企业搜索入口：

```text
http://www.027zpw.com/company/search.php
```

核心查询参数：

| 参数 | 含义 | 示例 |
|---|---|---|
| `kw` | 关键词 | `贸易` |
| `vip` | VIP 条件 | `0` |
| `type` | 企业类型条件 | `0` |
| `catid` | 行业分类 ID | `0` |
| `mode` | 经营模式条件 | `0` |
| `areaid` | 地区 ID | `0` |
| `size` | 公司规模条件 | `1` |
| `mincapital` | 最低注册资本 | 空 |
| `maxcapital` | 最高注册资本 | 空 |
| `page` | 分页页码 | `1` |
| `x` / `y` | 搜索按钮坐标 | 可忽略或保留 |

样例 URL 中的 `x=29&y=24` 是表单提交按钮坐标，不是业务筛选条件。实现时可以保留原值以最大程度复现请求，也可以不传。业务上别拿它当字段，拿了就属于自己给自己挖坑。

### 3.2 自定义条件输入方式

系统需要支持两种输入方式。

#### 方式 A：直接粘贴完整搜索 URL

用户输入：

```text
http://www.027zpw.com/company/search.php?kw=%E8%B4%B8%E6%98%93&vip=0&type=0&catid=0&mode=0&areaid=0&size=1&mincapital=&maxcapital=&x=29&y=24
```

程序行为：

- 自动解析 query 参数；
- 自动识别 `kw`、`vip`、`type`、`catid`、`mode`、`areaid`、`size` 等条件；
- 自动补充 `page=1...N`；
- 将原始 URL 和解析后的条件写入 Excel 的 `run_log` 表。

适合一次性抓某个页面条件，门槛最低。

#### 方式 B：使用配置文件

推荐使用 YAML 或 JSON 配置多个采集任务。

示例：

```yaml
jobs:
  - name: trade_size_1
    keyword: 贸易
    filters:
      vip: 0
      type: 0
      catid: 0
      mode: 0
      areaid: 0
      size: 1
      mincapital: ""
      maxcapital: ""
    crawl_detail: true
    max_pages: null
    delay_seconds:
      min: 1.5
      max: 3.0
    output_name: 贸易_规模1_企业增强版.xlsx

  - name: alloy_all_area
    keyword: 合金
    filters:
      vip: 0
      type: 0
      catid: 0
      mode: 0
      areaid: 0
      size: 0
      mincapital: ""
      maxcapital: ""
    crawl_detail: true
    max_pages: 10
    delay_seconds:
      min: 1.5
      max: 3.0
    output_name: 合金_前10页_企业增强版.xlsx
```

程序行为：

- 每个 `job` 独立运行；
- 每个 `job` 独立输出 Excel；
- 支持 `max_pages` 限制页数，用于试跑；
- 支持 `crawl_detail` 控制是否进入企业主页；
- 支持多个关键词、多个地区、多个行业条件批量跑。

### 3.3 条件覆盖规则

如果同时提供完整 URL 和配置字段：

1. 先解析完整 URL；
2. 再用配置文件中的字段覆盖 URL 参数；
3. 最终请求参数写入 `run_log`。

这样既能复制网页条件，又能局部调整参数。别让用户在 URL 里手抠 `%E8%B4%B8%E6%98%93`，那玩意儿看久了像乱码在嘲讽人类。

## 4. 数据采集范围

### 4.1 搜索列表页字段

从每个搜索页的企业列表项中提取：

| 字段 | 来源 |
|---|---|
| `job_name` | 配置任务名 |
| `keyword` | 搜索关键词 |
| `page` | 当前页码 |
| `rank_in_page` | 当前页内排序 |
| `company_name` | `h2 a.Title` |
| `homepage_url` | `h2 a.Title[href]` |
| `username` | `homepage=` 参数 |
| `intro` | `.Biz-type` |
| `main_products` | `.sw-mod-allcompany-Service` |
| `business_type` | `.iconCollection` 中括号前内容，如 `贸易商` |
| `verified_status` | `.iconCollection` 中核实状态，如 `未核实` |
| `source_url` | 当前搜索页 URL |
| `fetched_at` | 抓取时间 |

### 4.2 企业公开主页增强字段

访问：

```text
http://www.027zpw.com/index.php?homepage={username}
```

提取公开字段：

| 字段 | 来源 |
|---|---|
| `detail_title` | 页面 `<title>` 或 `h1` |
| `detail_slogan` | 企业主页 `h4` |
| `meta_keywords` | `meta[name=keywords]` |
| `meta_description` | `meta[name=description]` |
| `company_description` | “公司介绍”正文 |
| `company_image_url` | 公司介绍图 |
| `visit_count` | 页脚访问量 |
| `homepage_status` | `success` / `failed` / `permission_denied` |
| `homepage_error` | 失败原因 |

不采集：

- 会员中心；
- 登录后可见字段；
- 权限不足的联系方式；
- 聊天接口；
- 任何需要绕过权限的内容。

## 5. Excel 输出设计

每个任务输出一个 Excel 文件。

### 5.1 `companies` 主表

主表是一行一个企业，包含列表字段和增强详情字段。

核心列：

```text
job_name
keyword
page
rank_in_page
company_name
homepage_url
username
intro
main_products
business_type
verified_status
detail_title
detail_slogan
meta_keywords
meta_description
company_description
company_image_url
visit_count
homepage_status
homepage_error
source_url
fetched_at
```

### 5.2 `failed_urls` 失败记录表

用于排查和重试：

```text
job_name
url
url_type
page
company_name
username
error_type
error_message
retry_count
failed_at
```

`url_type` 可取：

- `search_page`
- `company_homepage`

### 5.3 `run_log` 运行日志表

记录本次任务条件和结果：

```text
job_name
keyword
base_url
final_query_params
total_records_declared
total_pages_declared
max_pages
crawl_detail
started_at
finished_at
request_count
success_company_count
failed_url_count
dedupe_count
output_file
```

### 5.4 `raw_conditions` 条件快照表

保留用户原始输入，避免以后复盘时变成“我当时到底搜了个啥”的悬疑剧。

```text
job_name
input_type
input_url
input_config_json
normalized_params_json
```

## 6. 核心流程

```text
读取配置或 URL
  ↓
标准化搜索条件
  ↓
请求第一页
  ↓
解析总条数和总页数
  ↓
按 page=1...N 抓取列表页
  ↓
解析企业列表
  ↓
按 username/homepage_url 去重
  ↓
进入公开企业主页补充详情
  ↓
写入缓存
  ↓
导出 Excel
  ↓
输出运行日志和失败记录
```

## 7. 断点续跑

增强版必须支持断点续跑，否则跑 1700 多家公司，中途网络抖一下就从头再来，跟坐牢没区别。

建议机制：

- 每个任务创建一个本地缓存目录；
- 列表页 HTML 可选缓存；
- 已解析企业写入中间 CSV 或 SQLite；
- 已完成的 `homepage_url` 标记为 done；
- 失败 URL 记录重试次数；
- 重新运行时跳过已完成记录。

推荐缓存结构：

```text
work/cache/
  trade_size_1/
    search_pages/
      page_1.html
      page_2.html
    companies.sqlite
    failed_urls.csv
    run_state.json
```

如果只是一次性轻量运行，可以用 CSV 缓存；如果后续条件会很多，建议直接 SQLite，少给自己制造 Excel 地狱。

## 8. 请求与重试策略

默认策略：

| 项 | 策略 |
|---|---|
| 请求方式 | `GET` |
| User-Agent | 常规浏览器 UA |
| 超时 | `15 秒` |
| 重试 | 最多 `3 次` |
| 请求间隔 | 随机 `1.5-3.0 秒` |
| 并发 | 默认 `1` |
| 编码 | 优先读取页面声明 `UTF-8` |
| 失败处理 | 写入 `failed_urls` |

HTTP 状态处理：

| 状态 | 处理 |
|---|---|
| `200` | 解析 |
| `403` / `401` | 记录权限失败，不重试 |
| `404` | 记录页面不存在 |
| `429` | 加长等待后重试 |
| `5xx` | 重试 |
| 超时 | 重试 |

## 9. 解析规则

### 9.1 搜索结果页

企业列表项选择器：

```text
li.offer.paGetId
```

字段选择器：

```text
公司名：h2 a.Title
主页链接：h2 a.Title[href]
简介：.Biz-type
主营产品：.sw-mod-allcompany-Service
经营类型/核实状态：.iconCollection
分页：.pages cite
```

分页文本示例：

```text
共1765条/89页
```

解析出：

```text
total_records_declared = 1765
total_pages_declared = 89
```

### 9.2 企业主页

字段选择器：

```text
企业名：h1
主营摘要：h4
关键词：meta[name=keywords]
描述：meta[name=description]
公司介绍：标题为“公司介绍”后的 main_body 正文
访问量：页脚文本中的 “访问量:数字”
```

页面结构是老 DESTOON 模板，选择器要写得宽容一点，别一上来绑死 DOM 层级。老站 HTML 就像年久失修的楼梯，你踩太死，它真能给你断。

## 10. 去重规则

优先级：

1. `username`
2. `homepage_url`
3. `company_name + main_products`

同一企业出现在多个搜索条件时：

- 单任务内去重；
- 多任务可以选择保留重复，并增加 `job_name` 区分；
- 如果要跨任务合并，使用 `username` 做主键。

## 11. 命令行设计

建议脚本入口：

```text
python crawl_027zpw_companies.py --config configs/jobs.yml
```

也支持直接传 URL：

```text
python crawl_027zpw_companies.py --url "http://www.027zpw.com/company/search.php?kw=%E8%B4%B8%E6%98%93&vip=0&type=0&catid=0&mode=0&areaid=0&size=1&mincapital=&maxcapital=&x=29&y=24" --crawl-detail true
```

常用参数：

| 参数 | 说明 |
|---|---|
| `--config` | 配置文件路径 |
| `--url` | 单个搜索 URL |
| `--crawl-detail` | 是否抓企业主页 |
| `--max-pages` | 限制最大页数，试跑用 |
| `--output` | 输出 Excel 文件名 |
| `--resume` | 是否断点续跑 |
| `--delay-min` | 最小请求间隔 |
| `--delay-max` | 最大请求间隔 |

## 12. 试跑策略

正式跑之前先试跑，别上来就 89 页全量开爬，像没踩刹车的需求评审。

建议顺序：

1. `max_pages=1`，检查字段解析；
2. `max_pages=3`，检查分页和去重；
3. 开启 `crawl_detail=true`，抽样 20 家检查增强字段；
4. 全量运行；
5. 对 `failed_urls` 做一次重试；
6. 导出最终 Excel。

## 13. 验收标准

基础验收：

- 能从完整 URL 自动解析搜索条件；
- 能从配置文件定义多个搜索任务；
- 能按分页抓取搜索结果；
- 能解析总条数和总页数；
- 能导出 Excel；
- Excel 至少包含 `companies`、`failed_urls`、`run_log`、`raw_conditions` 四个 sheet。

增强验收：

- `crawl_detail=true` 时能进入公开企业主页补字段；
- 遇到联系方式权限页不会继续硬试；
- 支持断点续跑；
- 支持失败重试；
- 支持按 `username` 去重；
- 输出数量与页面声明数量大致一致，差异可解释。

样例 URL 的预期：

```text
关键词：贸易
声明总条数：1765
声明总页数：89
每页约：20 条
```

实际导出数量可能略有差异，原因包括页面临时变动、重复企业、企业主页失效、站点返回异常等。

## 14. 实施拆分

### 第一步：基础采集器

- 解析 URL / 配置；
- 构造分页 URL；
- 抓取搜索页；
- 解析列表字段；
- 导出 Excel。

### 第二步：增强详情采集

- 进入企业主页；
- 解析公开详情；
- 合并到主表；
- 增加失败记录。

### 第三步：健壮性

- 断点续跑；
- 请求重试；
- 本地缓存；
- 去重；
- 运行日志。

### 第四步：批量任务

- 多关键词；
- 多筛选条件；
- 多 Excel 输出；
- 可选跨任务汇总。

## 15. 推荐最终交付物

```text
configs/
  027zpw_jobs.example.yml

work/
  cache/

outputs/
  贸易_规模1_企业增强版.xlsx
  027zpw_run_log.xlsx

crawl_027zpw_companies.py
README.md
```

如果只是一次性任务，脚本可以保持单文件；如果后续经常变搜索条件，建议拆成：

```text
src/
  config.py
  fetcher.py
  parser.py
  exporter.py
  runner.py
```

一次性活儿别过度架构，长期复用也别写成一坨。架构这事儿就像收纳，东西少的时候箱子够用，东西多了还全堆床上，那就是灾难片。

