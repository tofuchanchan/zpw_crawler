from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from src.zpw_crawler.config import job_from_url, jobs_from_yaml_text
from src.zpw_crawler.fetcher import HttpFetcher
from src.zpw_crawler.runner import run_jobs


st.set_page_config(page_title="027zpw 企业采集器", page_icon="🔎", layout="wide")

DEFAULT_URL = (
    "http://www.027zpw.com/company/search.php?"
    "kw=%E8%B4%B8%E6%98%93&vip=0&type=0&catid=0&mode=0&areaid=0&size=1"
)


def main() -> None:
    st.title("027zpw 企业采集器")
    st.caption("公开搜索页与公开企业主页采集，导出结构化 Excel。")

    mode = st.sidebar.radio("任务输入方式", ["粘贴搜索 URL", "YAML 批量配置"], index=0)
    crawl_detail = st.sidebar.checkbox("抓取企业公开主页详情", value=True)
    max_pages = st.sidebar.number_input("最大抓取页数", min_value=1, max_value=500, value=1)
    delay_min, delay_max = st.sidebar.slider("请求间隔秒数", 0.0, 10.0, (1.5, 3.0), step=0.5)
    resume = st.sidebar.checkbox("启用断点续跑缓存", value=True)

    if mode == "粘贴搜索 URL":
        url = st.text_area("搜索 URL", value=DEFAULT_URL, height=110)
        output_name = st.text_input("输出文件名", value="027zpw_companies.xlsx")
        jobs = None
    else:
        uploaded = st.file_uploader("上传 YAML 配置", type=["yml", "yaml"])
        yaml_text = ""
        if uploaded is not None:
            yaml_text = uploaded.read().decode("utf-8")
        yaml_text = st.text_area("或直接粘贴 YAML", value=yaml_text, height=260)
        output_name = ""
        jobs = None

    left, right = st.columns([1, 2])
    with left:
        run_clicked = st.button("开始采集", type="primary", use_container_width=True)
    with right:
        st.info("建议先用 1-3 页试跑。全量抓详情会比较慢，别把公网应用当本地脚本硬怼。", icon="ℹ️")

    if not run_clicked:
        _render_empty_state()
        return

    try:
        if mode == "粘贴搜索 URL":
            jobs = [
                job_from_url(
                    url,
                    name="web_url_job",
                    crawl_detail=crawl_detail,
                    max_pages=int(max_pages),
                    delay_min=float(delay_min),
                    delay_max=float(delay_max),
                    output_name=output_name,
                    resume=resume,
                )
            ]
        else:
            jobs = jobs_from_yaml_text(yaml_text)
            for job in jobs:
                job.crawl_detail = crawl_detail
                job.max_pages = int(max_pages) if max_pages else job.max_pages
                job.delay.min = float(delay_min)
                job.delay.max = float(delay_max)
                job.resume = resume
    except Exception as exc:
        st.error(f"任务配置有问题：{exc}")
        return

    progress_bar = st.progress(0)
    log_box = st.empty()
    events: list[dict] = []

    def progress(event: dict) -> None:
        events.append(event)
        stage = event.get("stage", "")
        page = event.get("page", "")
        company_name = event.get("company_name", "")
        if stage == "fetch_company_homepage":
            total = event.get("total") or 1
            index = event.get("index") or 1
            progress_bar.progress(min(index / total, 1.0))
            log_box.write(f"正在补充详情：{index}/{total} {company_name}")
        elif page:
            progress_bar.progress(0.1)
            log_box.write(f"正在抓取列表页：第 {page} 页")
        elif stage == "finished":
            progress_bar.progress(1.0)
            log_box.write("采集完成")

    try:
        with st.spinner("正在采集，请保持页面打开..."):
            fetcher = HttpFetcher(timeout=8, max_retries=1)
            results = run_jobs(
                jobs,
                output_dir="outputs",
                cache_dir="work/cache",
                fetcher=fetcher,
                progress=progress,
            )
    except Exception as exc:
        st.error(f"采集失败：{exc}")
        if "ConnectTimeout" in str(exc) or "timed out" in str(exc):
            st.warning(
                "当前部署环境无法连接目标站 www.027zpw.com。"
                "这通常是目标站屏蔽云服务器出口或跨境网络不可达导致的，"
                "建议改用本地运行、Render/自有服务器，或部署在能访问该站点的网络环境。"
            )
        return

    for result in results:
        _render_result(result)


def _render_empty_state() -> None:
    st.subheader("运行前检查")
    st.write(
        "输入搜索 URL 或 YAML 配置后点击开始。MVP 版本适合小批量公开页面采集；"
        "全量任务建议部署到带后台 Worker 的服务，别让浏览器页面在那儿硬扛几十分钟。"
    )


def _render_result(result) -> None:
    st.subheader(f"结果：{result.job_name}")
    col1, col2, col3 = st.columns(3)
    col1.metric("企业数", len(result.companies))
    col2.metric("失败 URL", len(result.failed_urls))
    col3.metric("输出文件", result.output_path.name)

    if result.companies:
        st.dataframe(pd.DataFrame(result.companies).head(100), use_container_width=True)
    else:
        st.warning("没有解析到企业记录。")

    output_path = Path(result.output_path)
    if output_path.exists():
        st.download_button(
            "下载 Excel",
            data=output_path.read_bytes(),
            file_name=output_path.name,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )


if __name__ == "__main__":
    main()
