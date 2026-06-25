from __future__ import annotations

import argparse
from pathlib import Path

from src.zpw_crawler.config import job_from_url, jobs_from_config
from src.zpw_crawler.runner import run_jobs


def main() -> None:
    parser = argparse.ArgumentParser(description="027zpw 企业搜索增强版采集器")
    parser.add_argument("--config", help="YAML 配置文件路径")
    parser.add_argument("--url", help="完整搜索 URL")
    parser.add_argument("--crawl-detail", default="true", choices=["true", "false"])
    parser.add_argument("--max-pages", type=int, default=None)
    parser.add_argument("--output", default=None, help="单 URL 模式输出 Excel 文件名")
    parser.add_argument("--output-dir", default="outputs")
    parser.add_argument("--cache-dir", default="work/cache")
    parser.add_argument("--delay-min", type=float, default=1.5)
    parser.add_argument("--delay-max", type=float, default=3.0)
    parser.add_argument("--no-resume", action="store_true")
    args = parser.parse_args()

    if not args.config and not args.url:
        parser.error("必须提供 --config 或 --url")

    if args.config:
        jobs = jobs_from_config(args.config)
    else:
        jobs = [
            job_from_url(
                args.url,
                crawl_detail=args.crawl_detail == "true",
                max_pages=args.max_pages,
                delay_min=args.delay_min,
                delay_max=args.delay_max,
                output_name=args.output,
                resume=not args.no_resume,
            )
        ]

    def progress(event: dict) -> None:
        stage = event.get("stage", "")
        job_name = event.get("job_name", "")
        page = event.get("page")
        if page:
            print(f"[{job_name}] {stage}: page={page}")
        else:
            print(f"[{job_name}] {stage}")

    results = run_jobs(
        jobs,
        output_dir=Path(args.output_dir),
        cache_dir=Path(args.cache_dir),
        progress=progress,
    )
    for result in results:
        print(f"完成：{result.job_name} -> {result.output_path}")


if __name__ == "__main__":
    main()
