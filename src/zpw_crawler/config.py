from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse

import yaml


DEFAULT_BASE_URL = "http://www.027zpw.com/company/search.php"

SUPPORTED_FILTERS = (
    "vip",
    "type",
    "catid",
    "mode",
    "areaid",
    "size",
    "mincapital",
    "maxcapital",
    "x",
    "y",
)


@dataclass(slots=True)
class DelayConfig:
    min: float = 1.5
    max: float = 3.0

    @classmethod
    def from_mapping(cls, value: dict[str, Any] | None) -> "DelayConfig":
        if not value:
            return cls()
        min_delay = float(value.get("min", 1.5))
        max_delay = float(value.get("max", 3.0))
        if min_delay < 0:
            min_delay = 0
        if max_delay < min_delay:
            max_delay = min_delay
        return cls(min=min_delay, max=max_delay)


@dataclass(slots=True)
class CrawlJob:
    name: str
    keyword: str = ""
    base_url: str = DEFAULT_BASE_URL
    params: dict[str, str] = field(default_factory=dict)
    input_url: str = ""
    input_type: str = "config"
    crawl_detail: bool = True
    max_pages: int | None = None
    output_name: str | None = None
    delay: DelayConfig = field(default_factory=DelayConfig)
    resume: bool = True

    def normalized_params(self) -> dict[str, str]:
        params = dict(self.params)
        if self.keyword:
            params["kw"] = self.keyword
        return {key: "" if value is None else str(value) for key, value in params.items()}

    def search_url(self, page: int) -> str:
        params = self.normalized_params()
        params["page"] = str(page)
        return f"{self.base_url}?{urlencode(params, doseq=False)}"

    def safe_output_name(self) -> str:
        if self.output_name:
            return self.output_name
        name = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in self.name)
        return f"{name or '027zpw_companies'}.xlsx"


def parse_search_url(url: str) -> tuple[str, dict[str, str]]:
    parsed = urlparse(url.strip())
    if not parsed.scheme or not parsed.netloc:
        raise ValueError("请输入完整的搜索 URL，例如 http://www.027zpw.com/company/search.php?... ")
    base_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    raw_params = parse_qs(parsed.query, keep_blank_values=True)
    params = {key: values[-1] if values else "" for key, values in raw_params.items()}
    params.pop("page", None)
    return base_url, params


def job_from_url(
    url: str,
    *,
    name: str = "single_url_job",
    crawl_detail: bool = True,
    max_pages: int | None = None,
    delay_min: float = 1.5,
    delay_max: float = 3.0,
    output_name: str | None = None,
    resume: bool = True,
) -> CrawlJob:
    base_url, params = parse_search_url(url)
    keyword = params.get("kw", "")
    return CrawlJob(
        name=name,
        keyword=keyword,
        base_url=base_url,
        params=params,
        input_url=url,
        input_type="url",
        crawl_detail=crawl_detail,
        max_pages=max_pages,
        output_name=output_name,
        delay=DelayConfig(delay_min, delay_max),
        resume=resume,
    )


def jobs_from_config(path: str | Path) -> list[CrawlJob]:
    config_path = Path(path)
    with config_path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    return jobs_from_mapping(payload)


def jobs_from_yaml_text(text: str) -> list[CrawlJob]:
    payload = yaml.safe_load(text) or {}
    return jobs_from_mapping(payload)


def jobs_from_mapping(payload: dict[str, Any]) -> list[CrawlJob]:
    jobs_payload = payload.get("jobs")
    if not isinstance(jobs_payload, list) or not jobs_payload:
        raise ValueError("配置文件必须包含非空 jobs 列表")

    jobs: list[CrawlJob] = []
    for index, raw_job in enumerate(jobs_payload, start=1):
        if not isinstance(raw_job, dict):
            raise ValueError(f"第 {index} 个 job 不是对象")

        input_url = str(raw_job.get("url") or raw_job.get("input_url") or "").strip()
        if input_url:
            base_url, params = parse_search_url(input_url)
            input_type = "url+config"
        else:
            base_url = str(raw_job.get("base_url") or DEFAULT_BASE_URL)
            params = {}
            input_type = "config"

        filters = raw_job.get("filters") or {}
        if not isinstance(filters, dict):
            raise ValueError(f"第 {index} 个 job 的 filters 必须是对象")
        for key in SUPPORTED_FILTERS:
            if key in filters:
                params[key] = "" if filters[key] is None else str(filters[key])

        keyword = str(raw_job.get("keyword", params.get("kw", "")))
        if keyword:
            params["kw"] = keyword

        delay = DelayConfig.from_mapping(raw_job.get("delay_seconds"))
        max_pages = raw_job.get("max_pages")
        jobs.append(
            CrawlJob(
                name=str(raw_job.get("name") or f"job_{index}"),
                keyword=keyword,
                base_url=base_url,
                params={key: "" if value is None else str(value) for key, value in params.items()},
                input_url=input_url,
                input_type=input_type,
                crawl_detail=bool(raw_job.get("crawl_detail", True)),
                max_pages=int(max_pages) if max_pages not in (None, "") else None,
                output_name=raw_job.get("output_name"),
                delay=delay,
                resume=bool(raw_job.get("resume", True)),
            )
        )
    return jobs
