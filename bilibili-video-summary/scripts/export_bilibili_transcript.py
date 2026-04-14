#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import requests

from fetch_bilibili_video_context import USER_AGENT, extract_identifiers, fetch_context


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="导出 B站公开视频字幕，或对本地媒体做转写。")
    parser.add_argument("--url", help="B站视频 URL")
    parser.add_argument("--bvid", help="B站视频 BVID")
    parser.add_argument("--aid", help="B站视频 AID")
    parser.add_argument("--media", help="本地音视频文件路径；仅在无公开字幕时用于本地转写")
    parser.add_argument("--backend", choices=["auto", "public_subtitles", "faster_whisper"], default="auto")
    parser.add_argument("--format", choices=["txt", "markdown", "json", "srt"], default="markdown")
    parser.add_argument("--model", default="small", help="faster-whisper 模型名，默认 small")
    parser.add_argument("--language", default="zh", help="转写语言，默认 zh")
    parser.add_argument("--timezone", default="Asia/Shanghai")
    return parser.parse_args()


def bilibili_get_json(url: str, *, params: dict[str, object], referer: str) -> dict[str, object]:
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


def resolve_identifiers(args: argparse.Namespace) -> tuple[str | None, str | None]:
    bvid = args.bvid
    aid = args.aid
    if args.url:
        url_bvid, url_aid = extract_identifiers(args.url)
        bvid = bvid or url_bvid
        aid = aid or url_aid
    return bvid, aid


def fetch_public_subtitle_tracks(*, bvid: str | None, aid: str | None, cid: str, referer_bvid: str | None) -> list[dict[str, str]]:
    params: dict[str, object] = {"cid": cid}
    if bvid:
        params["bvid"] = bvid
        referer = f"https://www.bilibili.com/video/{referer_bvid or bvid}"
    elif aid:
        params["aid"] = aid
        referer = "https://www.bilibili.com/"
    else:
        raise RuntimeError("缺少 bvid / aid")
    player = bilibili_get_json("https://api.bilibili.com/x/player/v2", params=params, referer=referer)
    subtitle = player.get("subtitle") if isinstance(player.get("subtitle"), dict) else {}
    raw_tracks = subtitle.get("subtitles") if isinstance(subtitle.get("subtitles"), list) else []
    tracks: list[dict[str, str]] = []
    for item in raw_tracks:
        if not isinstance(item, dict):
            continue
        subtitle_url = str(item.get("subtitle_url") or item.get("url") or "").strip()
        if not subtitle_url:
            continue
        if subtitle_url.startswith("//"):
            subtitle_url = f"https:{subtitle_url}"
        elif subtitle_url.startswith("/"):
            subtitle_url = f"https://api.bilibili.com{subtitle_url}"
        tracks.append(
            {
                "lan": str(item.get("lan") or "").strip(),
                "lan_doc": str(item.get("lan_doc") or "").strip(),
                "subtitle_url": subtitle_url,
            }
        )
    return tracks


def fetch_public_subtitle_segments(track: dict[str, str]) -> list[dict[str, object]]:
    response = requests.get(
        track["subtitle_url"],
        headers={"User-Agent": USER_AGENT, "Referer": "https://www.bilibili.com/"},
        timeout=20,
    )
    response.raise_for_status()
    payload = response.json()
    body = payload.get("body")
    if not isinstance(body, list):
        raise RuntimeError("字幕 JSON 结构异常：缺少 body")
    segments: list[dict[str, object]] = []
    for item in body:
        if not isinstance(item, dict):
            continue
        segments.append(
            {
                "from": float(item.get("from") or 0),
                "to": float(item.get("to") or 0),
                "text": str(item.get("content") or "").strip(),
            }
        )
    return segments


def transcribe_local_media(media_path: Path, *, model_name: str, language: str) -> list[dict[str, object]]:
    if not media_path.exists():
        raise RuntimeError(f"本地媒体文件不存在：{media_path}")
    try:
        from faster_whisper import WhisperModel
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(
            "未安装 faster-whisper。请先执行 `py -3 -m pip install faster-whisper`，然后重试。"
        ) from exc

    model = WhisperModel(model_name, device="auto", compute_type="int8")
    result, _info = model.transcribe(str(media_path), language=language, vad_filter=True)
    segments: list[dict[str, object]] = []
    for segment in result:
        segments.append(
            {
                "from": float(segment.start),
                "to": float(segment.end),
                "text": str(segment.text or "").strip(),
            }
        )
    return segments


def format_seconds(value: float) -> str:
    total_ms = int(round(value * 1000))
    total_seconds, milliseconds = divmod(total_ms, 1000)
    minutes, seconds = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"


def render_txt(segments: list[dict[str, object]]) -> str:
    return "\n".join(str(segment["text"]) for segment in segments if str(segment.get("text") or "").strip())


def render_srt(segments: list[dict[str, object]]) -> str:
    lines: list[str] = []
    for index, segment in enumerate(segments, 1):
        lines.append(str(index))
        lines.append(f"{format_seconds(float(segment['from']))} --> {format_seconds(float(segment['to']))}")
        lines.append(str(segment["text"]))
        lines.append("")
    return "\n".join(lines).rstrip()


def render_markdown(context: dict[str, object], source_kind: str, segments: list[dict[str, object]]) -> str:
    video = context["video"]
    assert isinstance(video, dict)
    lines = [
        "# B站视频字幕稿",
        "",
        f"- 标题：{video['title']}",
        f"- 作者：{video['owner_name']}",
        f"- 发布时间：{video['published_at'] or '未知'}",
        f"- 链接：{video['url']}",
        f"- 字幕来源：{source_kind}",
        "",
        "## 字幕正文",
        render_txt(segments) or "无",
    ]
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    bvid, aid = resolve_identifiers(args)
    context = fetch_context(bvid=bvid, aid=aid, timezone_name=args.timezone)
    video = context["video"]
    assert isinstance(video, dict)

    source_kind = ""
    segments: list[dict[str, object]] = []

    if args.backend in {"auto", "public_subtitles"}:
        tracks = fetch_public_subtitle_tracks(
            bvid=str(video.get("bvid") or "") or None,
            aid=str(video.get("aid") or "") or None,
            cid=str(video.get("cid") or ""),
            referer_bvid=str(video.get("bvid") or "") or None,
        )
        if tracks:
            segments = fetch_public_subtitle_segments(tracks[0])
            language = tracks[0].get("lan_doc") or tracks[0].get("lan") or "unknown"
            source_kind = f"公开字幕（{language}）"
        elif args.backend == "public_subtitles":
            raise RuntimeError("当前视频没有公开字幕轨。")

    if not segments and args.backend in {"auto", "faster_whisper"}:
        if args.media:
            segments = transcribe_local_media(Path(args.media), model_name=args.model, language=args.language)
            source_kind = f"本地转写（faster-whisper/{args.model}）"
        elif args.backend == "faster_whisper":
            raise RuntimeError("使用 faster-whisper 时必须提供 --media 本地文件路径。")

    if not segments:
        raise RuntimeError("当前视频没有公开字幕轨，且未提供可转写的本地媒体文件。")

    if args.format == "json":
        print(
            json.dumps(
                {
                    "video": context["video"],
                    "source_kind": source_kind,
                    "segment_count": len(segments),
                    "segments": segments,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    if args.format == "txt":
        print(render_txt(segments))
        return 0
    if args.format == "srt":
        print(render_srt(segments))
        return 0
    print(render_markdown(context, source_kind, segments))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
