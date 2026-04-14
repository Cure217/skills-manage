#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from urllib.parse import parse_qs, urlparse

try:
    import requests
except Exception as exc:  # pragma: no cover
    print(f"requests unavailable: {exc}", file=sys.stderr)
    raise


USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="抓取 B站视频公开元数据、章节点与字幕可用性。")
    parser.add_argument("--url", help="B站视频 URL")
    parser.add_argument("--bvid", help="B站视频 BVID")
    parser.add_argument("--aid", help="B站视频 AID")
    parser.add_argument("--format", choices=["json", "markdown"], default="json")
    parser.add_argument("--timezone", default="Asia/Shanghai")
    return parser.parse_args()


def extract_identifiers(url: str) -> tuple[str | None, str | None]:
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    bvid_match = re.search(r"(BV[0-9A-Za-z]+)", url)
    aid_match = re.search(r"(?:/av|aid=)(\d+)", url)
    bvid = bvid_match.group(1) if bvid_match else None
    aid = aid_match.group(1) if aid_match else None
    if not bvid:
        query_bvid = query.get("bvid")
        if query_bvid:
            bvid = query_bvid[0]
    if not aid:
        query_aid = query.get("aid")
        if query_aid:
            aid = query_aid[0]
    return bvid, aid


def bilibili_get(url: str, *, params: dict[str, object], referer: str) -> dict[str, object]:
    response = requests.get(
        url,
        params=params,
        headers={
            "User-Agent": USER_AGENT,
            "Referer": referer,
            "Accept": "application/json,text/plain,*/*",
        },
        timeout=20,
    )
    response.raise_for_status()
    payload = response.json()
    if payload.get("code") != 0:
        raise RuntimeError(f"B站接口返回异常: {payload.get('message') or payload.get('code')}")
    data = payload.get("data")
    if not isinstance(data, dict):
        raise RuntimeError("B站接口返回 data 结构异常")
    return data


def format_timestamp(timestamp: int | float | None, timezone_name: str) -> str | None:
    if not timestamp:
        return None
    timezone = dt.timezone(dt.timedelta(hours=8), name=timezone_name)
    return dt.datetime.fromtimestamp(int(timestamp), timezone).isoformat()


def format_duration(seconds: int | None) -> str | None:
    if seconds is None:
        return None
    minutes, second = divmod(int(seconds), 60)
    hour, minute = divmod(minutes, 60)
    if hour > 0:
        return f"{hour}小时{minute}分{second}秒"
    return f"{minute}分{second}秒"


def fetch_context(*, bvid: str | None, aid: str | None, timezone_name: str) -> dict[str, object]:
    params: dict[str, object] = {}
    if bvid:
        params["bvid"] = bvid
    elif aid:
        params["aid"] = aid
    else:
        raise RuntimeError("缺少 bvid / aid")

    view = bilibili_get(
        "https://api.bilibili.com/x/web-interface/view",
        params=params,
        referer="https://www.bilibili.com/",
    )
    canonical_bvid = str(view.get("bvid") or bvid or "")
    canonical_aid = str(view.get("aid") or aid or "")
    cid = view.get("cid")
    if not cid:
        raise RuntimeError("视频缺少 cid，无法继续抓取播放器信息")

    player = bilibili_get(
        "https://api.bilibili.com/x/player/v2",
        params={"bvid": canonical_bvid, "cid": cid},
        referer=f"https://www.bilibili.com/video/{canonical_bvid}",
    )

    owner = view.get("owner") if isinstance(view.get("owner"), dict) else {}
    stat = view.get("stat") if isinstance(view.get("stat"), dict) else {}
    subtitle = player.get("subtitle") if isinstance(player.get("subtitle"), dict) else {}
    subtitles = subtitle.get("subtitles") if isinstance(subtitle.get("subtitles"), list) else []
    chapters_raw = player.get("view_points") if isinstance(player.get("view_points"), list) else []

    chapters: list[dict[str, object]] = []
    for chapter in chapters_raw:
        if not isinstance(chapter, dict):
            continue
        chapters.append(
            {
                "from": int(chapter.get("from") or 0),
                "to": int(chapter.get("to") or 0),
                "content": str(chapter.get("content") or "").strip(),
            }
        )

    return {
        "video": {
            "title": str(view.get("title") or "").strip(),
            "url": f"https://www.bilibili.com/video/{canonical_bvid}",
            "bvid": canonical_bvid,
            "aid": canonical_aid,
            "cid": str(cid),
            "owner_name": str(owner.get("name") or "").strip(),
            "owner_mid": str(owner.get("mid") or "").strip(),
            "published_at": format_timestamp(view.get("pubdate"), timezone_name),
            "duration_seconds": int(view.get("duration") or 0),
            "duration_human": format_duration(int(view.get("duration") or 0)),
            "description": str(view.get("desc") or "").strip(),
            "stats": {
                "view": int(stat.get("view") or 0),
                "like": int(stat.get("like") or 0),
                "favorite": int(stat.get("favorite") or 0),
                "coin": int(stat.get("coin") or 0),
                "share": int(stat.get("share") or 0),
                "reply": int(stat.get("reply") or 0),
            },
            "ai_disclosure": str((view.get("argue_info") or {}).get("argue_msg") or "").strip()
            if isinstance(view.get("argue_info"), dict)
            else "",
        },
        "public_subtitles": {
            "available": bool(subtitles),
            "count": len(subtitles),
            "languages": [
                {
                    "lan": str(item.get("lan") or "").strip(),
                    "lan_doc": str(item.get("lan_doc") or "").strip(),
                }
                for item in subtitles
                if isinstance(item, dict)
            ],
        },
        "chapters": chapters,
        "summary_basis": [
            "video metadata",
            "video description",
            "official chapters",
            "public subtitle availability",
        ],
    }


def render_markdown(context: dict[str, object]) -> str:
    video = context["video"]
    subtitles = context["public_subtitles"]
    chapters = context["chapters"]
    assert isinstance(video, dict)
    assert isinstance(subtitles, dict)
    assert isinstance(chapters, list)
    stats = video["stats"]
    assert isinstance(stats, dict)
    lines = [
        "# B站视频公开上下文",
        "",
        f"- 标题：{video['title']}",
        f"- 作者：{video['owner_name']}",
        f"- 发布时间：{video['published_at'] or '未知'}",
        f"- 时长：{video['duration_human'] or '未知'}",
        f"- 链接：{video['url']}",
        f"- 字幕可用：{'是' if subtitles.get('available') else '否'}",
        f"- 基础数据：播放 {stats['view']} / 点赞 {stats['like']} / 收藏 {stats['favorite']} / 分享 {stats['share']}",
        "",
        "## 简介",
        video["description"] or "无",
        "",
        "## 官方章节点",
    ]
    if chapters:
        for chapter in chapters:
            assert isinstance(chapter, dict)
            lines.append(f"- {chapter['from']}s - {chapter['to']}s：{chapter['content']}")
    else:
        lines.append("- 无")
    lines += [
        "",
        "## 说明",
        "- 该输出仅包含公开可访问元数据、章节点与字幕可用性。",
        "- 若无公开字幕，后续摘要应明确基于简介和章节点判断。",
    ]
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    bvid = args.bvid
    aid = args.aid
    if args.url:
        url_bvid, url_aid = extract_identifiers(args.url)
        bvid = bvid or url_bvid
        aid = aid or url_aid
    context = fetch_context(bvid=bvid, aid=aid, timezone_name=args.timezone)
    if args.format == "markdown":
        print(render_markdown(context))
        return 0
    print(json.dumps(context, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
