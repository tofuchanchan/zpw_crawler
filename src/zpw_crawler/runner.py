from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from .config import CrawlJob
from .exporter import export_excel
from .fetcher import FetchError, HttpFetcher
from .parser import dedupe_key, parse_company_homepage, parse_search_page, parse_total_counts


ProgressCallback = Callable[[dict[str, Any]], None]
DETAIL_SCHEMA_VERSION = 2


@dataclass(slots=True)
class CrawlResult:
    job_name: str
    output_path: Path
    companies: list[dict[str, Any]] = field(default_factory=list)
    failed_urls: list[dict[str, Any]] = field(default_factory=list)
    run_log: list[dict[str, Any]] = field(default_factory=list)
    raw_conditions: list[dict[str, Any]] = field(default_factory=list)


class CrawlCache:
    def __init__(self, path: Path) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self._ensure_schema()

    def close(self) -> None:
        self.conn.close()

    def _ensure_schema(self) -> None:
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS companies (
                dedupe_key TEXT PRIMARY KEY,
                payload TEXT NOT NULL,
                detail_done INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL
            )
            """
        )
        self.conn.commit()

    def load_companies(self) -> dict[str, dict[str, Any]]:
        rows = self.conn.execute("SELECT dedupe_key, payload FROM companies").fetchall()
        return {row["dedupe_key"]: json.loads(row["payload"]) for row in rows}

    def upsert_company(self, key: str, row: dict[str, Any], *, detail_done: bool = False) -> None:
        self.conn.execute(
            """
            INSERT INTO companies (dedupe_key, payload, detail_done, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(dedupe_key) DO UPDATE SET
                payload = excluded.payload,
                detail_done = MAX(companies.detail_done, excluded.detail_done),
                updated_at = excluded.updated_at
            """,
            (key, json.dumps(row, ensure_ascii=False), int(detail_done), datetime.now().isoformat()),
        )
        self.conn.commit()

    def is_detail_done(self, key: str) -> bool:
        row = self.conn.execute(
            "SELECT detail_done FROM companies WHERE dedupe_key = ?",
            (key,),
        ).fetchone()
        return bool(row and row["detail_done"])


def run_jobs(
    jobs: list[CrawlJob],
    *,
    output_dir: str | Path = "outputs",
    cache_dir: str | Path = "work/cache",
    fetcher: HttpFetcher | None = None,
    progress: ProgressCallback | None = None,
) -> list[CrawlResult]:
    results: list[CrawlResult] = []
    for job in jobs:
        results.append(
            run_job(
                job,
                output_dir=output_dir,
                cache_dir=cache_dir,
                fetcher=fetcher,
                progress=progress,
            )
        )
    return results


def run_job(
    job: CrawlJob,
    *,
    output_dir: str | Path = "outputs",
    cache_dir: str | Path = "work/cache",
    fetcher: HttpFetcher | None = None,
    progress: ProgressCallback | None = None,
) -> CrawlResult:
    fetcher = fetcher or HttpFetcher()
    started_at = datetime.now()
    request_count = 0
    failed_urls: list[dict[str, Any]] = []
    raw_conditions = [
        {
            "job_name": job.name,
            "input_type": job.input_type,
            "input_url": job.input_url,
            "input_config_json": "",
            "normalized_params_json": json.dumps(job.normalized_params(), ensure_ascii=False),
        }
    ]

    cache = CrawlCache(Path(cache_dir) / job.name / "companies.sqlite")
    companies_by_key = cache.load_companies() if job.resume else {}
    dedupe_count = 0
    total_records_declared: int | None = None
    total_pages_declared: int | None = None

    try:
        first_url = job.search_url(1)
        _emit(progress, stage="fetch_search_page", job_name=job.name, page=1, url=first_url)
        first_response = fetcher.fetch(first_url, job.delay)
        request_count += 1
        total_records_declared, total_pages_declared = parse_total_counts(first_response.text)
        pages_to_fetch = _resolve_pages(total_pages_declared, job.max_pages)

        for page in range(1, pages_to_fetch + 1):
            if page == 1:
                html = first_response.text
                source_url = first_response.url
            else:
                url = job.search_url(page)
                _emit(progress, stage="fetch_search_page", job_name=job.name, page=page, url=url)
                try:
                    response = fetcher.fetch(url, job.delay)
                    request_count += 1
                    html = response.text
                    source_url = response.url
                except FetchError as exc:
                    failed_urls.append(_failed_row(job, exc.url, "search_page", page, "", "", exc))
                    continue

            rows = parse_search_page(
                html,
                job_name=job.name,
                keyword=job.keyword,
                page=page,
                source_url=source_url,
                fetched_at=datetime.now(),
            )
            for row in rows:
                key = dedupe_key(row)
                if key in companies_by_key:
                    if _merge_missing_list_fields(companies_by_key[key], row):
                        cache.upsert_company(key, companies_by_key[key], detail_done=cache.is_detail_done(key))
                    dedupe_count += 1
                    continue
                companies_by_key[key] = row
                cache.upsert_company(key, row, detail_done=False)
            _emit(progress, stage="parsed_search_page", job_name=job.name, page=page, rows=len(rows))

        if job.crawl_detail:
            for index, (key, row) in enumerate(list(companies_by_key.items()), start=1):
                if job.resume and cache.is_detail_done(key) and row.get("_detail_schema_version") == DETAIL_SCHEMA_VERSION:
                    continue
                homepage_url = row.get("homepage_url") or _homepage_from_username(row.get("username", ""))
                introduce_url = _with_file(homepage_url, "introduce")
                if not introduce_url:
                    continue
                _emit(
                    progress,
                    stage="fetch_company_homepage",
                    job_name=job.name,
                    index=index,
                    total=len(companies_by_key),
                    company_name=row.get("company_name", ""),
                )
                try:
                    response = fetcher.fetch(introduce_url, job.delay)
                    request_count += 1
                    detail = parse_company_homepage(response.text, page_url=response.url)
                    row.update(detail)
                    row["_detail_schema_version"] = DETAIL_SCHEMA_VERSION
                    cache.upsert_company(key, row, detail_done=detail.get("homepage_status") == "success")
                except FetchError as exc:
                    row.update({"homepage_status": "failed", "homepage_error": exc.message})
                    failed_urls.append(
                        _failed_row(
                            job,
                            introduce_url,
                            "company_homepage",
                            int(row.get("page") or 0),
                            row.get("company_name", ""),
                            row.get("username", ""),
                            exc,
                        )
                    )
                    cache.upsert_company(key, row, detail_done=False)

        companies = list(companies_by_key.values())
        output_path = Path(output_dir) / job.safe_output_name()
        finished_at = datetime.now()
        run_log = [
            {
                "job_name": job.name,
                "keyword": job.keyword,
                "base_url": job.base_url,
                "final_query_params": json.dumps(job.normalized_params(), ensure_ascii=False),
                "total_records_declared": total_records_declared,
                "total_pages_declared": total_pages_declared,
                "max_pages": job.max_pages,
                "crawl_detail": job.crawl_detail,
                "started_at": started_at.isoformat(timespec="seconds"),
                "finished_at": finished_at.isoformat(timespec="seconds"),
                "request_count": request_count,
                "success_company_count": len(companies),
                "failed_url_count": len(failed_urls),
                "dedupe_count": dedupe_count,
                "output_file": str(output_path),
            }
        ]
        export_excel(
            output_path,
            companies=companies,
            failed_urls=failed_urls,
            run_log=run_log,
            raw_conditions=raw_conditions,
        )
        _emit(progress, stage="finished", job_name=job.name, output_file=str(output_path))
        return CrawlResult(job.name, output_path, companies, failed_urls, run_log, raw_conditions)
    finally:
        cache.close()


def _resolve_pages(total_pages: int | None, max_pages: int | None) -> int:
    if total_pages is None or total_pages < 1:
        total_pages = 1
    if max_pages is None:
        return total_pages
    return max(1, min(total_pages, max_pages))


def _homepage_from_username(username: str) -> str:
    if not username:
        return ""
    return f"http://www.027zpw.com/index.php?homepage={username}"


def _with_file(homepage_url: str, file_name: str) -> str:
    if not homepage_url:
        return ""
    from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

    parsed = urlparse(homepage_url)
    params = dict(parse_qsl(parsed.query, keep_blank_values=True))
    params["file"] = file_name
    return urlunparse(parsed._replace(query=urlencode(params)))


def _merge_missing_list_fields(existing: dict[str, Any], parsed: dict[str, Any]) -> bool:
    changed = False
    for field in ("list_address", "phone"):
        if not existing.get(field) and parsed.get(field):
            existing[field] = parsed[field]
            changed = True
    return changed


def _failed_row(
    job: CrawlJob,
    url: str,
    url_type: str,
    page: int,
    company_name: str,
    username: str,
    exc: FetchError,
) -> dict[str, Any]:
    return {
        "job_name": job.name,
        "url": url,
        "url_type": url_type,
        "page": page,
        "company_name": company_name,
        "username": username,
        "error_type": exc.error_type,
        "error_message": exc.message,
        "retry_count": exc.retry_count,
        "failed_at": datetime.now().isoformat(timespec="seconds"),
    }


def _emit(progress: ProgressCallback | None, **event: Any) -> None:
    if progress:
        progress(event)
