from __future__ import annotations

import re
from datetime import datetime
from typing import Any
from urllib.parse import parse_qs, urljoin, urlparse

from bs4 import BeautifulSoup, Tag


def _text(node: Tag | None) -> str:
    if not node:
        return ""
    return " ".join(node.get_text(" ", strip=True).split())


def _attr(node: Tag | None, name: str) -> str:
    if not node:
        return ""
    value = node.get(name)
    return str(value or "").strip()


def _first(soup: BeautifulSoup | Tag, selectors: tuple[str, ...]) -> Tag | None:
    for selector in selectors:
        found = soup.select_one(selector)
        if found:
            return found
    return None


def parse_username(homepage_url: str) -> str:
    query = parse_qs(urlparse(homepage_url).query, keep_blank_values=True)
    values = query.get("homepage")
    return values[-1] if values else ""


def parse_total_counts(html: str) -> tuple[int | None, int | None]:
    soup = BeautifulSoup(html, "lxml")
    candidates = [_text(node) for node in soup.select(".pages cite, .pages")]
    candidates.append(_text(soup.body) if soup.body else soup.get_text(" ", strip=True))

    for text in candidates:
        compact = re.sub(r"\s+", "", text)
        match = re.search(r"共(\d+)条[/／](\d+)页", compact)
        if match:
            return int(match.group(1)), int(match.group(2))
        match = re.search(r"共(\d+)条.*?(\d+)页", compact)
        if match:
            return int(match.group(1)), int(match.group(2))
    return None, None


def parse_icon_collection(value: str) -> tuple[str, str]:
    text = " ".join(value.split())
    if not text:
        return "", ""

    verified_match = re.search(r"(已核实|未核实|已认证|未认证)", text)
    verified_status = verified_match.group(1) if verified_match else ""
    business_type = text
    if verified_status:
        business_type = business_type.replace(verified_status, "")
    business_type = re.sub(r"[\[\]【】()（）]", " ", business_type)
    business_type = " ".join(business_type.split())
    return business_type, verified_status


def parse_search_page(
    html: str,
    *,
    job_name: str,
    keyword: str,
    page: int,
    source_url: str,
    fetched_at: datetime,
) -> list[dict[str, Any]]:
    soup = BeautifulSoup(html, "lxml")
    items = soup.select("li.offer.paGetId")
    if not items:
        items = soup.select("li.offer, .offer.paGetId")

    rows: list[dict[str, Any]] = []
    for rank, item in enumerate(items, start=1):
        link = _first(item, ("h2 a.Title", "a.Title", "h2 a"))
        company_name = _text(link)
        href = _attr(link, "href")
        homepage_url = urljoin(source_url, href) if href else ""
        username = parse_username(homepage_url)
        intro = _text(_first(item, (".Biz-type", ".biz-type")))
        main_products = _text(_first(item, (".sw-mod-allcompany-Service", ".allcompany-Service")))
        business_type, verified_status = parse_icon_collection(_text(_first(item, (".iconCollection",))))

        if not company_name and not homepage_url:
            continue

        rows.append(
            {
                "job_name": job_name,
                "keyword": keyword,
                "page": page,
                "rank_in_page": rank,
                "company_name": company_name,
                "homepage_url": homepage_url,
                "username": username,
                "intro": intro,
                "main_products": main_products,
                "business_type": business_type,
                "verified_status": verified_status,
                "detail_title": "",
                "detail_slogan": "",
                "meta_keywords": "",
                "meta_description": "",
                "company_description": "",
                "company_image_url": "",
                "visit_count": "",
                "homepage_status": "",
                "homepage_error": "",
                "source_url": source_url,
                "fetched_at": fetched_at.isoformat(timespec="seconds"),
            }
        )
    return rows


def parse_company_homepage(html: str, *, page_url: str) -> dict[str, str]:
    soup = BeautifulSoup(html, "lxml")
    full_text = soup.get_text(" ", strip=True)
    if "无权查看" in full_text or "会员组无权" in full_text:
        return {"homepage_status": "permission_denied", "homepage_error": "权限不足"}

    title = _text(_first(soup, ("h1",))) or _text(soup.title)
    slogan = _text(_first(soup, ("h4",)))
    meta_keywords = _attr(soup.select_one('meta[name="keywords"]'), "content")
    meta_description = _attr(soup.select_one('meta[name="description"]'), "content")

    description_node = _find_company_description_node(soup)
    company_description = _text(description_node)
    image_url = ""
    if description_node:
        image = description_node.select_one("img")
        image_url = urljoin(page_url, _attr(image, "src")) if image else ""
    if not image_url:
        image = _first(soup, (".main_body img", ".content img", ".box_body img"))
        image_url = urljoin(page_url, _attr(image, "src")) if image else ""

    visit_count = ""
    visit_match = re.search(r"访问量[:：\s]*(\d+)", full_text)
    if visit_match:
        visit_count = visit_match.group(1)

    return {
        "detail_title": title,
        "detail_slogan": slogan,
        "meta_keywords": meta_keywords,
        "meta_description": meta_description,
        "company_description": company_description,
        "company_image_url": image_url,
        "visit_count": visit_count,
        "homepage_status": "success",
        "homepage_error": "",
    }


def _find_company_description_node(soup: BeautifulSoup) -> Tag | None:
    direct = _first(soup, (".main_body", ".box_body", ".content", "#content"))
    if direct and "公司介绍" in _text(direct):
        return direct

    for node in soup.find_all(string=re.compile("公司介绍")):
        parent = node.parent
        if not isinstance(parent, Tag):
            continue
        for sibling in parent.find_all_next(limit=6):
            if isinstance(sibling, Tag) and _text(sibling):
                return sibling
        return parent

    return direct


def dedupe_key(row: dict[str, Any]) -> str:
    if row.get("username"):
        return f"username:{row['username']}"
    if row.get("homepage_url"):
        return f"url:{row['homepage_url']}"
    return f"name_products:{row.get('company_name', '')}|{row.get('main_products', '')}"
