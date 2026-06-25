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
        list_address = _extract_labeled_value(item, ("地址",))
        phone = _extract_labeled_value(item, ("电话", "联系电话", "公司电话", "手机", "移动电话"))
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
                "list_address": list_address,
                "phone": phone,
                "detail_title": "",
                "detail_slogan": "",
                "meta_keywords": "",
                "meta_description": "",
                "company_description": "",
                "company_image_url": "",
                "profile_company_name": "",
                "profile_company_type": "",
                "profile_location": "",
                "profile_company_size": "",
                "profile_registered_capital": "",
                "profile_registered_year": "",
                "profile_data_certification": "",
                "profile_security_deposit": "",
                "profile_business_model": "",
                "profile_business_scope": "",
                "profile_selling_products": "",
                "profile_main_industries": "",
                "profile_fields_json": "",
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

    profile_fields = parse_company_profile(soup)

    return {
        "detail_title": title,
        "detail_slogan": slogan,
        "meta_keywords": meta_keywords,
        "meta_description": meta_description,
        "company_description": company_description,
        "company_image_url": image_url,
        "profile_company_name": profile_fields.get("公司名称", ""),
        "profile_company_type": profile_fields.get("公司类型", ""),
        "profile_location": profile_fields.get("所在地", ""),
        "profile_company_size": profile_fields.get("公司规模", ""),
        "profile_registered_capital": profile_fields.get("注册资本", ""),
        "profile_registered_year": profile_fields.get("注册年份", ""),
        "profile_data_certification": profile_fields.get("资料认证", ""),
        "profile_security_deposit": profile_fields.get("保证金", ""),
        "profile_business_model": profile_fields.get("经营模式", ""),
        "profile_business_scope": profile_fields.get("经营范围", ""),
        "profile_selling_products": profile_fields.get("销售的产品", ""),
        "profile_main_industries": profile_fields.get("主营行业", ""),
        "profile_fields_json": _json_dumps(profile_fields),
        "visit_count": visit_count,
        "homepage_status": "success",
        "homepage_error": "",
    }


def parse_company_profile(soup: BeautifulSoup) -> dict[str, str]:
    profile_body = _find_section_body(soup, "公司档案")
    if not profile_body:
        return {}

    fields: dict[str, str] = {}
    for label_cell in profile_body.select("td.f_b"):
        label = _normalize_label(_text(label_cell))
        if not label:
            continue
        value_cell = _next_td(label_cell)
        if not value_cell:
            continue
        fields[label] = _profile_value(value_cell)
    return fields


def _extract_labeled_value(container: Tag, labels: tuple[str, ...]) -> str:
    normalized_labels = {_normalize_label(label) for label in labels}
    for node in container.select(".Address, div, p, span"):
        label_node = node.find("em", recursive=False)
        if not label_node:
            continue
        label = _normalize_label(_text(label_node))
        if label not in normalized_labels:
            continue
        text = _text(node)
        label_text = _text(label_node)
        value = text.replace(label_text, "", 1).strip()
        return value.strip(":： ")
    return ""


def _find_company_description_node(soup: BeautifulSoup) -> Tag | None:
    section_body = _find_section_body(soup, "公司介绍")
    if section_body:
        return section_body

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


def _find_section_body(soup: BeautifulSoup, title: str) -> Tag | None:
    for strong in soup.find_all("strong"):
        if _text(strong) != title:
            continue
        head = strong.find_parent(class_="main_head")
        if head:
            sibling = head.find_next_sibling()
            while isinstance(sibling, Tag):
                classes = sibling.get("class", [])
                if "main_body" in classes:
                    return sibling
                sibling = sibling.find_next_sibling()
        for sibling in strong.find_all_next(limit=8):
            if isinstance(sibling, Tag) and "main_body" in sibling.get("class", []):
                return sibling
    return None


def _next_td(cell: Tag) -> Tag | None:
    sibling = cell.find_next_sibling()
    while sibling and not (isinstance(sibling, Tag) and sibling.name == "td"):
        sibling = sibling.find_next_sibling()
    return sibling if isinstance(sibling, Tag) else None


def _normalize_label(value: str) -> str:
    return re.sub(r"\s+", "", value).rstrip(":：")


def _profile_value(cell: Tag) -> str:
    nested_cells = cell.select("table td")
    if nested_cells:
        values = [_text(nested) for nested in nested_cells]
        return " | ".join(value for value in values if value)

    value = _text(cell)
    image_titles = [_attr(image, "title") for image in cell.select("img") if _attr(image, "title")]
    if image_titles:
        value = " ".join(part for part in [value, " ".join(image_titles)] if part)
    return value


def _json_dumps(value: dict[str, str]) -> str:
    if not value:
        return ""
    import json

    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def dedupe_key(row: dict[str, Any]) -> str:
    if row.get("username"):
        return f"username:{row['username']}"
    if row.get("homepage_url"):
        return f"url:{row['homepage_url']}"
    return f"name_products:{row.get('company_name', '')}|{row.get('main_products', '')}"
