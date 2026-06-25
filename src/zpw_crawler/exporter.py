from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd


COMPANY_COLUMNS = [
    "job_name",
    "keyword",
    "page",
    "rank_in_page",
    "company_name",
    "homepage_url",
    "username",
    "intro",
    "main_products",
    "business_type",
    "verified_status",
    "list_address",
    "phone",
    "detail_title",
    "detail_slogan",
    "meta_keywords",
    "meta_description",
    "company_description",
    "company_image_url",
    "profile_company_name",
    "profile_company_type",
    "profile_location",
    "profile_company_size",
    "profile_registered_capital",
    "profile_registered_year",
    "profile_data_certification",
    "profile_security_deposit",
    "profile_business_model",
    "profile_business_scope",
    "profile_selling_products",
    "profile_main_industries",
    "profile_fields_json",
    "visit_count",
    "homepage_status",
    "homepage_error",
    "source_url",
    "fetched_at",
]

FAILED_COLUMNS = [
    "job_name",
    "url",
    "url_type",
    "page",
    "company_name",
    "username",
    "error_type",
    "error_message",
    "retry_count",
    "failed_at",
]

RUN_LOG_COLUMNS = [
    "job_name",
    "keyword",
    "base_url",
    "final_query_params",
    "total_records_declared",
    "total_pages_declared",
    "max_pages",
    "crawl_detail",
    "started_at",
    "finished_at",
    "request_count",
    "success_company_count",
    "failed_url_count",
    "dedupe_count",
    "output_file",
]

RAW_CONDITIONS_COLUMNS = [
    "job_name",
    "input_type",
    "input_url",
    "input_config_json",
    "normalized_params_json",
]


def to_dataframe(rows: list[dict[str, Any]], columns: list[str]) -> pd.DataFrame:
    return pd.DataFrame(rows).reindex(columns=columns)


def export_excel(
    output_path: str | Path,
    *,
    companies: list[dict[str, Any]],
    failed_urls: list[dict[str, Any]],
    run_log: list[dict[str, Any]],
    raw_conditions: list[dict[str, Any]],
) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        to_dataframe(companies, COMPANY_COLUMNS).to_excel(writer, sheet_name="companies", index=False)
        to_dataframe(failed_urls, FAILED_COLUMNS).to_excel(writer, sheet_name="failed_urls", index=False)
        to_dataframe(run_log, RUN_LOG_COLUMNS).to_excel(writer, sheet_name="run_log", index=False)
        to_dataframe(raw_conditions, RAW_CONDITIONS_COLUMNS).to_excel(
            writer, sheet_name="raw_conditions", index=False
        )
    return path
