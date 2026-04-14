#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import parse_qsl, urljoin, urlparse, urlunparse, urlencode

try:
    import requests
except Exception:
    requests = None

from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
DEFAULT_CONFIG_PATH = SKILL_DIR / "references" / "sources.json"

SECTION_ORDER = [
    "重大模型/产品发布",
    "官方公告/能力更新",
    "开源项目/代码趋势",
    "行业热点/讨论",
    "低可信/待验证信息",
]

SECTION_PRIORITY = {name: index for index, name in enumerate(SECTION_ORDER)}
CONFIDENCE_PRIORITY = {"high": 3, "medium": 2, "low": 1}
MODEL_KEYWORDS = [
    "release",
    "launch",
    "launches",
    "launched",
    "announce",
    "announced",
    "introducing",
    "preview",
    "availability",
    "available",
    "agent",
    "agents",
    "reasoning",
    "multimodal",
    "model",
    "models",
    "api",
    "sdk",
    "gpt",
    "claude",
    "gemini",
    "veo",
    "imagen",
    "lyria",
    "gemma",
    "qwen",
    "deepseek",
    "llama",
    "mistral",
    "sora",
]
TRACKING_QUERY_KEYS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_content",
    "utm_term",
    "utm_id",
    "feature",
    "si",
    "ref",
    "trk",
    "fbclid",
    "gclid",
}
FIXED_TIMEZONE_FALLBACKS = {
    "Asia/Shanghai": dt.timezone(dt.timedelta(hours=8), name="Asia/Shanghai"),
    "UTC": dt.timezone.utc,
}


class FetchError(RuntimeError):
    pass


def log(verbose: bool, message: str) -> None:
    if verbose:
        print(f"[daily-ai-news] {message}", file=sys.stderr)


def resolve_timezone(name: str) -> dt.tzinfo:
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError:
        if name in FIXED_TIMEZONE_FALLBACKS:
            return FIXED_TIMEZONE_FALLBACKS[name]
        raise


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="按日期聚合 AI 资讯并输出结构化日报。")
    parser.add_argument("--preset", choices=["today", "yesterday"], help="快捷日期。")
    parser.add_argument("--date", help="指定日期，格式 YYYY-MM-DD。")
    parser.add_argument("--days", type=int, help="最近 N 天。")
    parser.add_argument("--start", help="开始日期，格式 YYYY-MM-DD。")
    parser.add_argument("--end", help="结束日期，格式 YYYY-MM-DD。")
    parser.add_argument("--timezone", default="Asia/Shanghai", help="时区，默认 Asia/Shanghai。")
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown", help="输出格式。")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH), help="来源配置文件。")
    parser.add_argument("--limit-per-source", type=int, help="覆盖配置里的单源默认抓取上限。")
    parser.add_argument("--verbose", action="store_true", help="输出抓取日志。")
    return parser.parse_args()


def parse_date_token(token: str | None, timezone: dt.tzinfo) -> dt.date:
    if token is None:
        raise ValueError("日期不能为空。")
    value = token.strip().lower()
    now = dt.datetime.now(timezone)
    if value == "today":
        return now.date()
    if value == "yesterday":
        return now.date() - dt.timedelta(days=1)
    return dt.date.fromisoformat(token)


def build_query_window(args: argparse.Namespace) -> dict[str, object]:
    timezone = resolve_timezone(args.timezone)
    now = dt.datetime.now(timezone)
    selected = [bool(args.preset), bool(args.date), bool(args.days), bool(args.start or args.end)]
    if sum(selected) > 1:
        raise ValueError("--preset / --date / --days / --start+--end 只能使用一种。")
    if args.start or args.end:
        if not (args.start and args.end):
            raise ValueError("--start 和 --end 必须一起提供。")
        start_date = parse_date_token(args.start, timezone)
        end_date = parse_date_token(args.end, timezone)
        if end_date < start_date:
            raise ValueError("结束日期不能早于开始日期。")
        start_dt = dt.datetime.combine(start_date, dt.time.min, timezone)
        end_dt = dt.datetime.combine(end_date, dt.time.max, timezone)
        if end_date == now.date():
            end_dt = now
        label = f"{start_date.isoformat()} 至 {end_date.isoformat()}"
        request_kind = "range"
    elif args.days:
        if args.days < 1:
            raise ValueError("--days 必须 >= 1。")
        end_date = now.date()
        start_date = end_date - dt.timedelta(days=args.days - 1)
        start_dt = dt.datetime.combine(start_date, dt.time.min, timezone)
        end_dt = now
        label = f"最近 {args.days} 天"
        request_kind = "days"
    elif args.date:
        target_date = parse_date_token(args.date, timezone)
        start_dt = dt.datetime.combine(target_date, dt.time.min, timezone)
        end_dt = dt.datetime.combine(target_date, dt.time.max, timezone)
        if target_date == now.date():
            end_dt = now
        label = target_date.isoformat()
        request_kind = "date"
    elif args.preset == "yesterday":
        target_date = now.date() - dt.timedelta(days=1)
        start_dt = dt.datetime.combine(target_date, dt.time.min, timezone)
        end_dt = dt.datetime.combine(target_date, dt.time.max, timezone)
        label = "昨天"
        request_kind = "preset"
    else:
        target_date = now.date()
        start_dt = dt.datetime.combine(target_date, dt.time.min, timezone)
        end_dt = now
        label = "今天"
        request_kind = "preset"
    return {
        "timezone": args.timezone,
        "tzinfo": timezone,
        "start": start_dt,
        "end": end_dt,
        "label": label,
        "request_kind": request_kind,
        "generated_at": now,
    }


def load_config(path: str) -> dict[str, object]:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def find_curl() -> str:
    candidate = shutil.which("curl.exe") or shutil.which("curl")
    if not candidate:
        raise FetchError("未找到 curl，可执行抓取器不可用。")
    return candidate


def curl_fetch(
    url: str,
    timeout_seconds: int,
    user_agent: str,
    headers: dict[str, str] | None = None,
    insecure: bool = False,
) -> str:
    curl_bin = find_curl()
    command = [
        curl_bin,
        "-L",
        "-sS",
        "--max-time",
        str(timeout_seconds),
        "-A",
        user_agent,
    ]
    if insecure:
        command.append("-k")
    for key, value in (headers or {}).items():
        command.extend(["-H", f"{key}: {value}"])
    command.append(url)
    completed = subprocess.run(command, capture_output=True, text=False, check=False)
    if completed.returncode != 0:
        stderr = completed.stderr.decode("utf-8", errors="replace").strip()
        raise FetchError(stderr or f"curl 返回非零退出码: {completed.returncode}")
    return completed.stdout.decode("utf-8", errors="replace")


def requests_fetch(
    url: str,
    timeout_seconds: int,
    user_agent: str,
    headers: dict[str, str] | None = None,
    insecure: bool = False,
) -> str:
    if requests is None:
        raise FetchError("requests unavailable")
    merged_headers = {"User-Agent": user_agent}
    for key, value in (headers or {}).items():
        merged_headers[str(key)] = str(value)
    try:
        response = requests.get(url, headers=merged_headers, timeout=timeout_seconds, verify=not insecure)
        response.raise_for_status()
        response.encoding = response.encoding or response.apparent_encoding or "utf-8"
        return response.text
    except Exception as exc:
        raise FetchError(str(exc))


def fetch_text(source: dict[str, object], defaults: dict[str, object]) -> str:
    timeout_seconds = int(defaults.get("request_timeout_seconds", 25))
    user_agent = str(defaults.get("user_agent", "daily-ai-news-skill/1.0"))
    headers = source.get("headers", {})
    url = source.get("url")
    if not isinstance(url, str) or not url:
        raise FetchError("来源缺少 url。")
    try:
        return requests_fetch(url, timeout_seconds, user_agent, headers=headers if isinstance(headers, dict) else None, insecure=False)
    except FetchError:
        pass
    try:
        return curl_fetch(url, timeout_seconds, user_agent, headers=headers if isinstance(headers, dict) else None, insecure=False)
    except FetchError:
        if source.get("allow_insecure_tls"):
            try:
                return requests_fetch(url, timeout_seconds, user_agent, headers=headers if isinstance(headers, dict) else None, insecure=True)
            except FetchError:
                return curl_fetch(url, timeout_seconds, user_agent, headers=headers if isinstance(headers, dict) else None, insecure=True)
        raise


def clean_text(value: str | None) -> str:
    if not value:
        return ""
    text = html.unescape(value)
    text = re.sub(r"<script[\s\S]*?</script>", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"<style[\s\S]*?</style>", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def truncate_text(value: str, length: int = 220) -> str:
    text = clean_text(value)
    if len(text) <= length:
        return text
    return text[: length - 1].rstrip() + "…"


def canonicalize_url(url: str) -> str:
    parsed = urlparse(url)
    query = [(key, value) for key, value in parse_qsl(parsed.query, keep_blank_values=True) if key not in TRACKING_QUERY_KEYS]
    return urlunparse(
        (
            parsed.scheme,
            parsed.netloc.lower(),
            parsed.path.rstrip("/"),
            parsed.params,
            urlencode(query, doseq=True),
            "",
        )
    )


def normalize_title(value: str) -> str:
    lowered = clean_text(value).lower()
    lowered = re.sub(r"[\W_]+", " ", lowered)
    lowered = re.sub(r"\s+", " ", lowered)
    return lowered.strip()


def parse_datetime(value: str | None, timezone: dt.tzinfo) -> tuple[dt.datetime | None, str]:
    text = clean_text(value)
    if not text:
        return None, "unknown"
    candidates = [text]
    if text.endswith("Z"):
        candidates.append(text.replace("Z", "+00:00"))
    for candidate in candidates:
        try:
            parsed = parsedate_to_datetime(candidate)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone)
            return parsed.astimezone(timezone), "datetime"
        except (TypeError, ValueError, IndexError):
            pass
        try:
            parsed = dt.datetime.fromisoformat(candidate)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone)
            return parsed.astimezone(timezone), "datetime"
        except ValueError:
            pass
    for fmt in ("%Y-%m-%d|%H:%M", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S"):
        try:
            parsed = dt.datetime.strptime(text, fmt).replace(tzinfo=timezone)
            return parsed, "datetime"
        except ValueError:
            pass
    for fmt in ("%Y-%m-%d", "%b %d, %Y", "%B %d, %Y"):
        try:
            parsed_date = dt.datetime.strptime(text, fmt).date()
            parsed = dt.datetime.combine(parsed_date, dt.time(hour=12), timezone)
            return parsed, "day"
        except ValueError:
            pass
    for fmt in ("%b %Y", "%B %Y"):
        try:
            parsed_date = dt.datetime.strptime(text, fmt).date().replace(day=1)
            parsed = dt.datetime.combine(parsed_date, dt.time(hour=12), timezone)
            return parsed, "month"
        except ValueError:
            pass
    return None, "unknown"


def matches_window(
    published_at: dt.datetime | None,
    precision: str,
    observed_at: dt.datetime | None,
    window: dict[str, object],
) -> bool:
    start = window["start"]
    end = window["end"]
    assert isinstance(start, dt.datetime)
    assert isinstance(end, dt.datetime)
    if published_at is not None:
        if precision == "month":
            return (end - start) >= dt.timedelta(days=28) and start.date().month == published_at.date().month
        return start <= published_at <= end
    if observed_at is not None:
        return start <= observed_at <= end
    return False


def section_for_item(item: dict[str, object]) -> str:
    if item["confidence"] == "low":
        return "低可信/待验证信息"
    title = normalize_title(str(item["title"]))
    if item["source_type"] == "open-source":
        return "开源项目/代码趋势"
    if item["source_type"] in {"social", "video"}:
        return "行业热点/讨论"
    if any(keyword in title for keyword in MODEL_KEYWORDS):
        return "重大模型/产品发布"
    if item["source_type"] == "official":
        return "官方公告/能力更新"
    return str(item.get("section_bias") or "行业热点/讨论")


def build_conclusion(item: dict[str, object]) -> str:
    title = str(item["title"])
    source_name = str(item["source_name"])
    if item["section"] == "重大模型/产品发布":
        return f"{source_name} 有新的模型或产品级更新，重点关注“{title}”的能力范围、可用性与发布时间。"
    if item["source_type"] == "official":
        return f"{source_name} 发布了官方更新“{title}”，适合作为高可信一手信息优先阅读。"
    if item["source_type"] == "open-source":
        return f"{source_name} 出现新的开源动态“{title}”，适合跟踪版本、仓库活跃度与生态变化。"
    if item["source_type"] == "video":
        return f"{source_name} 发布了新视频“{title}”，可作为产品演示或行业讨论线索。"
    if item["source_type"] == "social":
        return f"{source_name} 出现讨论线索“{title}”，需要结合原始链接继续核实。"
    return f"{source_name} 出现新动态“{title}”。"


def build_summary(item: dict[str, object]) -> str:
    summary = clean_text(str(item.get("summary") or ""))
    if summary:
        return truncate_text(summary, 220)
    extras = []
    for key in ("content_category", "primary_tag", "repo"):
        value = item.get(key)
        if value:
            extras.append(str(value))
    if extras:
        return " / ".join(extras)
    if item["source_type"] == "video":
        return "默认从官方频道视频流提取，适合作为产品演示、发布会或访谈线索。"
    if item["source_type"] == "open-source":
        return "默认从 GitHub 版本更新或热榜中提取，适合作为工程侧变化线索。"
    return "原始来源未提供更完整摘要，建议打开原链接查看上下文。"


def extract_html_paragraphs(html_text: str, limit: int = 4) -> list[str]:
    paragraphs = re.findall(r"<p[^>]*>([\s\S]*?)</p>", html_text, flags=re.IGNORECASE)
    cleaned: list[str] = []
    for paragraph in paragraphs:
        text = clean_text(paragraph)
        if not text or len(text) < 20:
            continue
        cleaned.append(text)
        if len(cleaned) >= limit:
            break
    return cleaned


def create_item(
    source: dict[str, object],
    title: str,
    url: str,
    summary: str = "",
    raw_date: str = "",
    published_at: dt.datetime | None = None,
    date_precision: str = "unknown",
    observed_at: dt.datetime | None = None,
    extra: dict[str, object] | None = None,
) -> dict[str, object]:
    item = {
        "title": clean_text(title),
        "url": canonicalize_url(url),
        "summary": clean_text(summary),
        "raw_date": clean_text(raw_date),
        "published_dt": published_at,
        "date_precision": date_precision,
        "observed_dt": observed_at,
        "published_at": published_at.isoformat() if published_at else None,
        "observed_at": observed_at.isoformat() if observed_at else None,
        "source_id": source["id"],
        "source_name": source["name"],
        "source_type": source["source_type"],
        "platform": source.get("platform"),
        "confidence": source.get("confidence", "medium"),
        "section_bias": source.get("section_bias"),
        "priority": source.get("priority", 0),
        "also_seen_on": [],
    }
    if extra:
        item.update(extra)
    item["section"] = section_for_item(item)
    item["one_line"] = build_conclusion(item)
    item["summary"] = build_summary(item)
    return item


def matches_source_keywords(source: dict[str, object], *parts: str) -> bool:
    keywords = [str(keyword).lower() for keyword in source.get("ai_keywords", []) if str(keyword).strip()]
    if not keywords:
        return True
    haystack = " ".join(clean_text(part) for part in parts if part).lower()
    return any(keyword in haystack for keyword in keywords)


def merge_headers(source: dict[str, object], extra: dict[str, str] | None = None) -> dict[str, str]:
    merged: dict[str, str] = {}
    for key, value in (source.get("headers") or {}).items():
        merged[str(key)] = str(value)
    for key, value in (extra or {}).items():
        merged[str(key)] = str(value)
    return merged


def extract_json_assignment(document: str, marker: str) -> dict[str, object]:
    marker_index = document.find(marker)
    if marker_index < 0:
        raise FetchError(f"未找到页面变量：{marker}")
    cursor = marker_index + len(marker)
    start = -1
    depth = 0
    in_string = False
    escaped = False
    for index in range(cursor, len(document)):
        char = document[index]
        if start < 0:
            if char.isspace():
                continue
            if char != "{":
                raise FetchError(f"{marker} 后不是 JSON 对象")
            start = index
            depth = 1
            continue
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == "\"":
                in_string = False
            continue
        if char == "\"":
            in_string = True
            continue
        if char == "{":
            depth += 1
            continue
        if char == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(document[start : index + 1])
                except json.JSONDecodeError as exc:
                    raise FetchError(f"页面 JSON 解析失败：{exc}") from exc
    raise FetchError(f"未完整解析 {marker} 对应的 JSON")


def resolve_bilibili_mid(source: dict[str, object]) -> str:
    mid = clean_text(str(source.get("mid") or ""))
    if mid:
        return mid
    url = str(source.get("url") or "")
    for pattern in (r"space\.bilibili\.com/(?P<mid>\d+)", r"www\.bilibili\.com/list/(?P<mid>\d+)"):
        match = re.search(pattern, url)
        if match:
            return match.group("mid")
    raise FetchError("B站来源缺少 mid，或 url 中无法解析 UP 主 mid")


def fetch_bilibili_up_videos(source: dict[str, object], defaults: dict[str, object], window: dict[str, object], verbose: bool) -> list[dict[str, object]]:
    mid = resolve_bilibili_mid(source)
    max_items = int(source.get("max_items", defaults.get("max_items_per_source", 12)))
    detail_fetch_limit = int(source.get("detail_fetch_limit", max(max_items * 4, max_items)))
    list_url = str(source.get("list_url") or f"https://www.bilibili.com/list/{mid}?sort_field=pubdate")
    list_headers = merge_headers(
        source,
        {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Referer": f"https://space.bilibili.com/{mid}/video",
        },
    )
    list_source = {**source, "url": list_url, "headers": list_headers}
    html_text = fetch_text(list_source, defaults)
    page_state = extract_json_assignment(html_text, "window.__INITIAL_STATE__=")
    resource_list = page_state.get("resourceList")
    if not isinstance(resource_list, list) or not resource_list:
        raise FetchError("未从 B站列表页解析到视频列表")

    timezone = window["tzinfo"]
    items: list[dict[str, object]] = []
    detail_attempts = 0
    detail_successes = 0
    for resource in resource_list[:detail_fetch_limit]:
        if not isinstance(resource, dict):
            continue
        bvid = clean_text(str(resource.get("bvid") or ""))
        if not bvid:
            continue
        detail_attempts += 1
        video_url = f"https://www.bilibili.com/video/{bvid}"
        detail_source = {
            **source,
            "url": f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}",
            "headers": merge_headers(
                source,
                {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
                    "Accept": "application/json,text/plain,*/*",
                    "Referer": video_url,
                },
            ),
        }
        try:
            payload = json.loads(fetch_text(detail_source, defaults))
        except (FetchError, json.JSONDecodeError) as exc:
            log(verbose, f"{source.get('name')}: bilibili view failed for {bvid}: {exc}")
            continue
        data = payload.get("data")
        if payload.get("code") != 0 or not isinstance(data, dict):
            log(verbose, f"{source.get('name')}: bilibili view returned non-zero code for {bvid}: {payload.get('message')}")
            continue
        detail_successes += 1
        title = clean_text(str(data.get("title") or resource.get("title") or ""))
        description = clean_text(str(data.get("desc") or ""))
        if not matches_source_keywords(source, title, description):
            continue
        published_dt: dt.datetime | None = None
        precision = "unknown"
        raw_date = ""
        timestamp = data.get("pubdate") or data.get("ctime")
        if isinstance(timestamp, (int, float)):
            published_dt = dt.datetime.fromtimestamp(int(timestamp), timezone)
            precision = "datetime"
            raw_date = published_dt.isoformat()
        else:
            raw_date = clean_text(str(timestamp or ""))
            published_dt, precision = parse_datetime(raw_date, timezone)
        owner = data.get("owner") if isinstance(data.get("owner"), dict) else {}
        summary_parts = [description, clean_text(str(resource.get("views") or ""))]
        item = create_item(
            source,
            title=title,
            url=video_url,
            summary=" / ".join(part for part in summary_parts if part),
            raw_date=raw_date,
            published_at=published_dt,
            date_precision=precision,
            extra={
                "author_name": owner.get("name"),
                "author_mid": owner.get("mid"),
                "bvid": bvid,
                "view_count": data.get("stat", {}).get("view") if isinstance(data.get("stat"), dict) else None,
                "content_category": "Bilibili Video",
            },
        )
        if matches_window(item["published_dt"], precision, item["observed_dt"], window):
            items.append(item)
        if len(items) >= max_items:
            break
    if detail_attempts > 0 and detail_successes == 0:
        raise FetchError("B站视频详情接口请求失败或返回受限")
    return items


def fetch_rss_items(source: dict[str, object], defaults: dict[str, object], window: dict[str, object], verbose: bool) -> list[dict[str, object]]:
    xml_text = fetch_text(source, defaults)
    root = ET.fromstring(xml_text)
    items: list[dict[str, object]] = []
    timezone = window["tzinfo"]
    max_items = int(source.get("max_items", defaults.get("max_items_per_source", 12)))
    if root.tag.lower().endswith("rss"):
        channel = root.find("channel")
        if channel is None:
            return []
        for raw_item in channel.findall("item"):
            title = raw_item.findtext("title") or ""
            link = raw_item.findtext("link") or ""
            summary = raw_item.findtext("description") or raw_item.findtext("{http://purl.org/rss/1.0/modules/content/}encoded") or ""
            raw_date = raw_item.findtext("pubDate") or raw_item.findtext("{http://purl.org/dc/elements/1.1/}date") or ""
            if not matches_source_keywords(source, title, summary):
                continue
            published_dt, precision = parse_datetime(raw_date, timezone)
            item = create_item(source, title, link, summary=summary, raw_date=raw_date, published_at=published_dt, date_precision=precision)
            if matches_window(item["published_dt"], precision, item["observed_dt"], window):
                items.append(item)
            if len(items) >= max_items:
                break
        return items
    atom_ns = {"atom": "http://www.w3.org/2005/Atom"}
    for entry in root.findall("atom:entry", atom_ns):
        title = entry.findtext("atom:title", default="", namespaces=atom_ns)
        link = ""
        for link_node in entry.findall("atom:link", atom_ns):
            href = link_node.attrib.get("href")
            if href:
                link = href
                break
        summary = entry.findtext("atom:summary", default="", namespaces=atom_ns) or entry.findtext("atom:content", default="", namespaces=atom_ns)
        raw_date = entry.findtext("atom:published", default="", namespaces=atom_ns) or entry.findtext("atom:updated", default="", namespaces=atom_ns)
        if not matches_source_keywords(source, title, summary):
            continue
        published_dt, precision = parse_datetime(raw_date, timezone)
        item = create_item(source, title, link, summary=summary, raw_date=raw_date, published_at=published_dt, date_precision=precision)
        if matches_window(item["published_dt"], precision, item["observed_dt"], window):
            items.append(item)
        if len(items) >= max_items:
            break
    return items


def fetch_github_releases(source: dict[str, object], defaults: dict[str, object], window: dict[str, object], verbose: bool) -> list[dict[str, object]]:
    repo = source.get("repo")
    if not isinstance(repo, str) or not repo:
        raise FetchError("GitHub Release 来源缺少 repo。")
    atom_source = {**source, "url": f"https://github.com/{repo}/releases.atom"}
    items = fetch_rss_items(atom_source, defaults, window, verbose)
    for item in items:
        item["repo"] = repo
        item["content_category"] = "GitHub Release"
        item["summary"] = build_summary(item)
    return items


def fetch_github_trending(source: dict[str, object], defaults: dict[str, object], window: dict[str, object], verbose: bool) -> list[dict[str, object]]:
    html_text = fetch_text(source, defaults)
    blocks = re.findall(r"<article class=\"Box-row\"[\s\S]*?</article>", html_text)
    items: list[dict[str, object]] = []
    observed_at = window["generated_at"]
    assert isinstance(observed_at, dt.datetime)
    keywords = [str(keyword).lower() for keyword in source.get("ai_keywords", [])]
    for block in blocks:
        href_match = re.search(r'href="/([^"/]+/[^"/]+)"', block)
        if not href_match:
            continue
        repo = href_match.group(1)
        if repo.startswith("sponsors/"):
            continue
        title = repo
        description_match = re.search(r"<p[^>]*>([\s\S]*?)</p>", block)
        description = clean_text(description_match.group(1)) if description_match else ""
        normalized = f"{title} {description}".lower()
        if keywords and not any(keyword in normalized for keyword in keywords):
            continue
        stars_today_match = re.search(r"(\d[\d,]*)\s+stars\s+today", clean_text(block), flags=re.IGNORECASE)
        summary = description
        if stars_today_match:
            summary = f"{description} 今日新增热度：{stars_today_match.group(1)} stars。".strip()
        item = create_item(
            source,
            title=title,
            url=f"https://github.com/{repo}",
            summary=summary,
            raw_date=observed_at.date().isoformat(),
            observed_at=observed_at,
            extra={"repo": repo, "content_category": "Trending"}
        )
        if matches_window(item["published_dt"], item["date_precision"], item["observed_dt"], window):
            items.append(item)
    return items[: int(source.get("max_items", defaults.get("max_items_per_source", 12)))]


def fetch_google_blog_listing(source: dict[str, object], defaults: dict[str, object], window: dict[str, object], verbose: bool) -> list[dict[str, object]]:
    html_text = fetch_text(source, defaults)
    pattern = re.compile(
        r"a4-analytics-[a-z\-]+='(?P<payload>\{.*?\})'[\s\S]{0,800}?href=\"(?P<href>https://blog\.google/[^\"]+)\"",
        re.IGNORECASE,
    )
    timezone = window["tzinfo"]
    seen: set[tuple[str, str]] = set()
    items: list[dict[str, object]] = []
    for match in pattern.finditer(html_text):
        payload_text = html.unescape(match.group("payload"))
        try:
            payload = json.loads(payload_text)
        except json.JSONDecodeError:
            continue
        href = canonicalize_url(match.group("href"))
        title = payload.get("article_name") or payload.get("link_text") or ""
        raw_date = payload.get("publish_date") or ""
        published_dt, precision = parse_datetime(str(raw_date), timezone)
        key = (str(title), href)
        if key in seen or not title:
            continue
        seen.add(key)
        item = create_item(
            source,
            title=str(title),
            url=href,
            summary=" / ".join(
                part for part in [payload.get("content_category"), payload.get("primary_tag"), payload.get("secondary_tags")] if part
            ),
            raw_date=str(raw_date),
            published_at=published_dt,
            date_precision=precision,
            extra={
                "content_category": payload.get("content_category"),
                "primary_tag": payload.get("primary_tag"),
                "author_name": payload.get("author_name"),
            },
        )
        if matches_window(item["published_dt"], precision, item["observed_dt"], window):
            items.append(item)
    return items


def fetch_deepmind_blog(source: dict[str, object], defaults: dict[str, object], window: dict[str, object], verbose: bool) -> list[dict[str, object]]:
    html_text = fetch_text(source, defaults)
    blocks = re.findall(r"<article[\s\S]*?</article>", html_text)
    timezone = window["tzinfo"]
    items: list[dict[str, object]] = []
    seen_urls: set[str] = set()
    for block in blocks:
        href_match = re.search(r'href=(?:"|\')?(?P<href>/blog/[^"\' >]+)', block)
        title_match = re.search(r"<h3[^>]*>(?P<title>[\s\S]*?)</h3>", block)
        time_match = re.search(r"<time[^>]*datetime=\"(?P<datetime>[^\"]+)\"[^>]*>(?P<label>[\s\S]*?)</time>", block)
        summary_match = re.search(r"<p[^>]*>(?P<summary>[\s\S]*?)</p>", block)
        if not href_match or not title_match:
            continue
        url = canonicalize_url(urljoin(str(source["url"]), href_match.group("href")))
        if url in seen_urls:
            continue
        seen_urls.add(url)
        raw_date = ""
        if time_match:
            raw_date = time_match.group("datetime") or clean_text(time_match.group("label"))
        published_dt, precision = parse_datetime(raw_date, timezone)
        item = create_item(
            source,
            title=title_match.group("title"),
            url=url,
            summary=summary_match.group("summary") if summary_match else "",
            raw_date=raw_date,
            published_at=published_dt,
            date_precision=precision,
        )
        if matches_window(item["published_dt"], precision, item["observed_dt"], window):
            items.append(item)
    return items


def fetch_anthropic_newsroom(source: dict[str, object], defaults: dict[str, object], window: dict[str, object], verbose: bool) -> list[dict[str, object]]:
    html_text = fetch_text(source, defaults)
    pattern = re.compile(
        r'<a href="(?P<href>/[^"]+)" class="[^"]*FeaturedGrid[^"]*"[^>]*>(?P<body>[\s\S]*?)</a>',
        re.IGNORECASE,
    )
    timezone = window["tzinfo"]
    items: list[dict[str, object]] = []
    seen_urls: set[str] = set()
    for match in pattern.finditer(html_text):
        body = match.group("body")
        title_match = re.search(r"<h[1-4][^>]*>(?P<title>[\s\S]*?)</h[1-4]>", body)
        time_match = re.search(r"<time[^>]*>(?P<time>[\s\S]*?)</time>", body)
        summary_match = re.search(r"<p[^>]*>(?P<summary>[\s\S]*?)</p>", body)
        if not title_match:
            continue
        url = canonicalize_url(urljoin(str(source["url"]), match.group("href")))
        if url.endswith("/news") or url in seen_urls:
            continue
        seen_urls.add(url)
        raw_date = clean_text(time_match.group("time")) if time_match else ""
        published_dt, precision = parse_datetime(raw_date, timezone)
        item = create_item(
            source,
            title=title_match.group("title"),
            url=url,
            summary=summary_match.group("summary") if summary_match else "",
            raw_date=raw_date,
            published_at=published_dt,
            date_precision=precision,
        )
        if matches_window(item["published_dt"], precision, item["observed_dt"], window):
            items.append(item)
    return items


def fetch_red_anthropic_blog(source: dict[str, object], defaults: dict[str, object], window: dict[str, object], verbose: bool) -> list[dict[str, object]]:
    html_text = fetch_text(source, defaults)
    blocks = re.findall(
        r'<a href="(?P<href>\d{4}/[^"]+/)" class="note">(?P<body>[\s\S]*?)</a>',
        html_text,
        flags=re.IGNORECASE,
    )
    timezone = window["tzinfo"]
    items: list[dict[str, object]] = []
    seen_urls: set[str] = set()
    for match in blocks:
        title_match = re.search(r"<h3[^>]*>(?P<title>[\s\S]*?)</h3>", match[1], flags=re.IGNORECASE)
        if not title_match:
            continue
        url = canonicalize_url(urljoin(str(source["url"]), match[0]))
        if url in seen_urls:
            continue
        seen_urls.add(url)
        summary = clean_text(match[1])
        raw_date = ""
        published_dt = None
        precision = "unknown"
        try:
            detail_html = fetch_text({"url": url, "allow_insecure_tls": True}, defaults)
            date_match = re.search(r"<p>\s*(?P<date>[A-Z][a-z]+ \d{1,2}, \d{4})\s*</p>", detail_html)
            if date_match:
                raw_date = date_match.group("date")
                published_dt, precision = parse_datetime(raw_date, timezone)
            paragraphs = extract_html_paragraphs(detail_html, limit=3)
            if paragraphs:
                summary = " ".join(paragraphs[:2])
        except Exception as exc:  # noqa: BLE001
            log(verbose, f"Red Anthropic detail fetch failed for {url}: {exc}")
        item = create_item(
            source,
            title=title_match.group("title"),
            url=url,
            summary=summary,
            raw_date=raw_date,
            published_at=published_dt,
            date_precision=precision,
        )
        if matches_window(item["published_dt"], precision, item["observed_dt"], window):
            items.append(item)
    return items


def resolve_youtube_feed(channel_url: str, defaults: dict[str, object]) -> str:
    if "feeds/videos.xml" in channel_url:
        return channel_url
    source = {"url": channel_url}
    channel_page = fetch_text(source, defaults)
    channel_id_match = re.search(r'"channelId":"(?P<channel>UC[\w\-]+)"', channel_page)
    if not channel_id_match:
        channel_id_match = re.search(r'"externalId":"(?P<channel>UC[\w\-]+)"', channel_page)
    if not channel_id_match:
        raise FetchError("无法从 YouTube 频道页解析 channelId。")
    return f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id_match.group('channel')}"


def fetch_youtube_channel(source: dict[str, object], defaults: dict[str, object], window: dict[str, object], verbose: bool) -> list[dict[str, object]]:
    feed_url = resolve_youtube_feed(str(source["url"]), defaults)
    feed_source = {**source, "url": feed_url}
    return fetch_rss_items(feed_source, defaults, window, verbose)


FETCHERS = {
    "rss": fetch_rss_items,
    "custom_rss": fetch_rss_items,
    "wechat_article_rss": fetch_rss_items,
    "wechat_mp_rss": fetch_rss_items,
    "github_releases": fetch_github_releases,
    "github_trending": fetch_github_trending,
    "google_blog_listing": fetch_google_blog_listing,
    "deepmind_blog": fetch_deepmind_blog,
    "anthropic_newsroom": fetch_anthropic_newsroom,
    "red_anthropic_blog": fetch_red_anthropic_blog,
    "bilibili_up_videos": fetch_bilibili_up_videos,
    "youtube_channel": fetch_youtube_channel,
}


def dedupe_items(items: list[dict[str, object]]) -> list[dict[str, object]]:
    deduped: list[dict[str, object]] = []
    by_url: dict[str, dict[str, object]] = {}
    by_title: dict[str, dict[str, object]] = {}
    sorted_items = sorted(
        items,
        key=lambda item: (
            -CONFIDENCE_PRIORITY.get(str(item["confidence"]), 0),
            -int(item.get("priority", 0)),
            str(item.get("published_at") or item.get("observed_at") or ""),
        ),
        reverse=False,
    )
    for item in sorted_items:
        url_key = str(item["url"])
        title_key = normalize_title(str(item["title"]))
        existing = by_url.get(url_key) or by_title.get(title_key)
        if existing:
            seen_names = {str(existing["source_name"]), *(str(name) for name in existing.get("also_seen_on", []))}
            if str(item["source_name"]) not in seen_names:
                existing.setdefault("also_seen_on", []).append(item["source_name"])
            if CONFIDENCE_PRIORITY.get(str(item["confidence"]), 0) > CONFIDENCE_PRIORITY.get(str(existing["confidence"]), 0):
                existing["confidence"] = item["confidence"]
            continue
        deduped.append(item)
        by_url[url_key] = item
        by_title[title_key] = item
    for item in deduped:
        item["section"] = section_for_item(item)
        item["one_line"] = build_conclusion(item)
    return deduped


def run_sources(config: dict[str, object], window: dict[str, object], args: argparse.Namespace) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    defaults = dict(config.get("defaults", {}))
    if args.limit_per_source:
        defaults["max_items_per_source"] = args.limit_per_source
    defaults["timezone"] = args.timezone
    results: list[dict[str, object]] = []
    statuses: list[dict[str, object]] = []
    for source in config.get("sources", []):
        name = str(source["name"])
        if not source.get("enabled", True):
            statuses.append({"source_id": source["id"], "source_name": name, "status": "disabled", "reason": source.get("reason", "未启用。")})
            log(args.verbose, f"{name}: disabled")
            continue
        fetcher_name = str(source.get("fetcher"))
        fetcher = FETCHERS.get(fetcher_name)
        if fetcher is None:
            statuses.append({"source_id": source["id"], "source_name": name, "status": "failed", "reason": f"未实现 fetcher: {fetcher_name}"})
            log(args.verbose, f"{name}: missing fetcher {fetcher_name}")
            continue
        try:
            items = fetcher(source, defaults, window, args.verbose)
            if items:
                results.extend(items)
                statuses.append({"source_id": source["id"], "source_name": name, "status": "ok", "count": len(items)})
                log(args.verbose, f"{name}: ok ({len(items)})")
            else:
                statuses.append({"source_id": source["id"], "source_name": name, "status": "no_result", "reason": "抓取成功，但查询日期范围内无结果。"})
                log(args.verbose, f"{name}: no result")
        except Exception as exc:  # noqa: BLE001
            statuses.append({"source_id": source["id"], "source_name": name, "status": "failed", "reason": str(exc)})
            log(args.verbose, f"{name}: failed ({exc})")
    return results, statuses


def pick_highlights(items: list[dict[str, object]]) -> list[str]:
    ranked = sorted(
        [item for item in items if item["section"] != "低可信/待验证信息"],
        key=lambda item: (
            SECTION_PRIORITY.get(str(item["section"]), 99),
            -CONFIDENCE_PRIORITY.get(str(item["confidence"]), 0),
            -int(item.get("priority", 0)),
            str(item.get("published_at") or item.get("observed_at") or ""),
        ),
    )
    return [f"{item['title']}（{item['source_name']}）" for item in ranked[:3]]


def build_report(items: list[dict[str, object]], statuses: list[dict[str, object]], window: dict[str, object]) -> dict[str, object]:
    deduped = dedupe_items(items)
    for item in deduped:
        item.pop("published_dt", None)
        item.pop("observed_dt", None)
    sections = {name: [] for name in SECTION_ORDER}
    for item in deduped:
        sections[str(item["section"])].append(item)
    for name, values in sections.items():
        values.sort(
            key=lambda item: (
                -CONFIDENCE_PRIORITY.get(str(item["confidence"]), 0),
                -int(item.get("priority", 0)),
                str(item.get("published_at") or item.get("observed_at") or ""),
            ),
            reverse=False,
        )
    status_counter = Counter(str(status["status"]) for status in statuses)
    type_counter = Counter(str(item["source_type"]) for item in deduped)
    return {
        "query": {
            "label": window["label"],
            "timezone": window["timezone"],
            "start": window["start"].isoformat(),
            "end": window["end"].isoformat(),
            "generated_at": window["generated_at"].isoformat(),
        },
        "highlights": pick_highlights(deduped),
        "sections": sections,
        "source_stats": {
            "attempted": len(statuses),
            "ok": status_counter.get("ok", 0),
            "no_result": status_counter.get("no_result", 0),
            "failed": status_counter.get("failed", 0),
            "disabled": status_counter.get("disabled", 0),
            "deduped_items": len(deduped),
            "by_source_type": dict(type_counter),
        },
        "source_statuses": statuses,
        "risks": [
            "默认时区按 Asia/Shanghai 处理。",
            "YouTube、X、B站及别名站点可能受网络、TLS、代理或凭据限制。",
            "GitHub Trending 属于观察值，不等同于正式发布时间。",
            "月粒度日期（例如仅有“December 2025”）在按日查询时默认不纳入结果。",
        ],
    }


def format_datetime(item: dict[str, object]) -> str:
    published_at = item.get("published_at")
    if published_at:
        return str(published_at)
    observed_at = item.get("observed_at")
    if observed_at:
        return f"{observed_at}（observed_at）"
    raw_date = item.get("raw_date")
    if raw_date:
        return str(raw_date)
    return "未知"


def render_markdown(report: dict[str, object]) -> str:
    query = report["query"]
    lines = [
        "# AI 资讯日报",
        "",
        f"- 日期与时区：{query['label']}（{query['timezone']}）",
        f"- 查询范围：{query['start']} ~ {query['end']}",
        f"- 生成时间：{query['generated_at']}",
        f"- 去重后资讯数：{report['source_stats']['deduped_items']}",
        (
            f"- 来源统计：已尝试 {report['source_stats']['attempted']} 个来源，"
            f"成功 {report['source_stats']['ok']}，无结果 {report['source_stats']['no_result']}，"
            f"失败 {report['source_stats']['failed']}，待配置/未启用 {report['source_stats']['disabled']}"
        ),
        "",
        "## 今日重点结论",
    ]
    if report["highlights"]:
        for highlight in report["highlights"]:
            lines.append(f"- {highlight}")
    else:
        lines.append("- 当日未形成足够明确的高可信重点，建议查看抓取失败/缺失来源。")
    for section_name in SECTION_ORDER:
        lines.extend(["", f"## {section_name}"])
        section_items = report["sections"][section_name]
        if not section_items:
            lines.append("- 无")
            continue
        for index, item in enumerate(section_items, start=1):
            lines.extend(
                [
                    f"### {index}. {item['title']}",
                    f"- 一句话结论：{item['one_line']}",
                    f"- 简短摘要：{item['summary'] or '无'}",
                    f"- 原始链接：{item['url']}",
                    f"- 来源名称：{item['source_name']}",
                    f"- 来源类型：{item['source_type']}",
                    f"- 对应日期或发布时间：{format_datetime(item)}",
                    f"- 可信度：{item['confidence']}",
                ]
            )
            if item.get("also_seen_on"):
                lines.append(f"- 重复来源：{', '.join(str(name) for name in item['also_seen_on'])}")
    lines.extend(["", "## 来源统计"])
    by_type = report["source_stats"]["by_source_type"]
    if by_type:
        for source_type, count in sorted(by_type.items()):
            lines.append(f"- {source_type}：{count}")
    else:
        lines.append("- 无")
    lines.extend(["", "## 抓取失败/缺失来源"])
    failed_like = [status for status in report["source_statuses"] if status["status"] != "ok"]
    if failed_like:
        for status in failed_like:
            lines.append(f"- {status['source_name']}：{status.get('reason', status['status'])}")
    else:
        lines.append("- 无")
    lines.extend(["", "## 风险与备注"])
    for risk in report["risks"]:
        lines.append(f"- {risk}")
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8")
        config = load_config(args.config)
        window = build_query_window(args)
        items, statuses = run_sources(config, window, args)
        report = build_report(items, statuses, window)
        if args.format == "json":
            print(json.dumps(report, ensure_ascii=False, indent=2))
        else:
            print(render_markdown(report))
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"[daily-ai-news] ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
