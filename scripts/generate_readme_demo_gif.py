from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parents[1]
ASSETS_DIR = ROOT / "assets"
GIF_PATH = ASSETS_DIR / "skills-manage-demo.gif"
PREVIEW_PATH = ASSETS_DIR / "skills-manage-demo-preview.png"

WIDTH = 1100
HEIGHT = 620

BACKGROUND_TOP = (10, 15, 28)
BACKGROUND_BOTTOM = (34, 18, 42)
CARD = (22, 31, 49)
CARD_ALT = (17, 24, 39)
TEXT = (241, 245, 255)
TEXT_MUTED = (174, 185, 210)
PURPLE = (139, 92, 246)
BLUE = (59, 130, 246)
GREEN = (16, 185, 129)
YELLOW = (245, 158, 11)
LINE = (76, 96, 138)

FONT_REGULAR = r"C:\Windows\Fonts\msyh.ttc"
FONT_BOLD = r"C:\Windows\Fonts\msyhbd.ttc"
FONT_CODE = r"C:\Windows\Fonts\consola.ttf"


def load_font(path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, size=size)


TITLE_FONT = load_font(FONT_BOLD, 40)
SUBTITLE_FONT = load_font(FONT_BOLD, 26)
SECTION_FONT = load_font(FONT_BOLD, 24)
TEXT_FONT = load_font(FONT_REGULAR, 18)
SMALL_FONT = load_font(FONT_REGULAR, 16)
CODE_FONT = load_font(FONT_CODE, 16)


def count_skills() -> tuple[int, int, int]:
    custom_count = sum(1 for child in ROOT.iterdir() if child.is_dir() and not child.name.startswith(".") and (child / "SKILL.md").exists())
    system_root = ROOT / ".system"
    system_count = sum(1 for child in system_root.iterdir() if child.is_dir() and (child / "SKILL.md").exists())
    return custom_count + system_count, custom_count, system_count


def draw_background() -> Image.Image:
    image = Image.new("RGB", (WIDTH, HEIGHT), BACKGROUND_TOP)
    draw = ImageDraw.Draw(image)
    for y in range(HEIGHT):
        ratio = y / max(HEIGHT - 1, 1)
        color = tuple(
            int(BACKGROUND_TOP[index] + (BACKGROUND_BOTTOM[index] - BACKGROUND_TOP[index]) * ratio)
            for index in range(3)
        )
        draw.line((0, y, WIDTH, y), fill=color)

    glow_specs = [
        ((110, 530, 360, 760), (65, 95, 255, 42), 55),
        ((720, 10, 1040, 330), (118, 56, 255, 52), 65),
        ((760, 370, 980, 590), (17, 185, 129, 34), 48),
    ]
    for box, color, blur_radius in glow_specs:
        overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        overlay_draw.ellipse(box, fill=color)
        overlay = overlay.filter(ImageFilter.GaussianBlur(blur_radius))
        image = Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")
    return image


def rounded_box(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], fill: tuple[int, int, int], outline: tuple[int, int, int] | None = None, width: int = 1, radius: int = 24) -> None:
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def write(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, font: ImageFont.FreeTypeFont, fill: tuple[int, int, int] = TEXT) -> None:
    draw.text(xy, text, font=font, fill=fill)


def multiline(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, font: ImageFont.FreeTypeFont, fill: tuple[int, int, int] = TEXT, spacing: int = 8) -> None:
    draw.multiline_text(xy, text, font=font, fill=fill, spacing=spacing)


def header(draw: ImageDraw.ImageDraw, right_label: str) -> None:
    write(draw, (70, 62), "skills-manage", TITLE_FONT)
    write(draw, (70, 118), "一个面向 Codex / Codex CLI 的本地 Skills 仓库", SUBTITLE_FONT)
    write(draw, (70, 158), "集中管理、版本化同步、持续维护你的 Skills 目录。", TEXT_FONT, TEXT_MUTED)
    rounded_box(draw, (748, 54, 1028, 112), fill=(17, 24, 41), outline=LINE, width=1, radius=22)
    write(draw, (780, 72), right_label, SECTION_FONT, GREEN)


def card(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], title: str, body: str, accent: tuple[int, int, int]) -> None:
    rounded_box(draw, box, fill=CARD, outline=accent, width=2)
    x1, y1, _, _ = box
    draw.rectangle((x1 + 18, y1 + 18, x1 + 28, y1 + 88), fill=accent)
    write(draw, (x1 + 48, y1 + 24), title, SECTION_FONT)
    multiline(draw, (x1 + 48, y1 + 62), body, TEXT_FONT, TEXT_MUTED, spacing=7)


def metric(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], value: str, label: str, accent: tuple[int, int, int]) -> None:
    rounded_box(draw, box, fill=CARD, outline=accent, width=2)
    x1, y1, _, _ = box
    write(draw, (x1 + 28, y1 + 26), value, TITLE_FONT, accent)
    write(draw, (x1 + 28, y1 + 84), label, TEXT_FONT, TEXT_MUTED)


def code_panel(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], title: str, code: str) -> None:
    rounded_box(draw, box, fill=CARD_ALT, outline=LINE, width=1)
    x1, y1, _, _ = box
    write(draw, (x1 + 22, y1 + 22), title, SMALL_FONT, TEXT_MUTED)
    multiline(draw, (x1 + 22, y1 + 60), code, CODE_FONT, TEXT, spacing=10)


def build_frame_overview() -> Image.Image:
    image = draw_background()
    draw = ImageDraw.Draw(image)
    _, custom_count, _ = count_skills()
    header(draw, f"{custom_count} 个自定义 Skills")

    card(
        draw,
        (70, 214, 350, 342),
        "集中管理",
        "把本地 `~/.codex/skills`\n从零散目录整理成可追踪仓库",
        PURPLE,
    )
    card(
        draw,
        (410, 214, 690, 342),
        "跨设备同步",
        "统一维护同一套 Skills\n新机器 clone 后即可直接使用",
        BLUE,
    )
    card(
        draw,
        (750, 214, 1030, 342),
        "持续沉淀",
        "把 Prompt、脚本、模板\n沉淀成长期可复用 Skill",
        GREEN,
    )

    code_panel(
        draw,
        (70, 396, 1030, 520),
        "Quick Start",
        "git clone https://github.com/Cure217/skills-manage.git ~/.codex/skills",
    )
    write(draw, (70, 568), "适合 Codex、Claude Code 与长期维护本地 AI 工作流的开发者。", TEXT_FONT, TEXT)
    return image


def build_frame_catalog() -> Image.Image:
    image = draw_background()
    draw = ImageDraw.Draw(image)
    total_count, custom_count, system_count = count_skills()
    header(draw, f"{system_count} 个系统 Skills 副本")

    metric(draw, (70, 220, 310, 352), str(total_count), "总技能数", PURPLE)
    metric(draw, (350, 220, 590, 352), str(custom_count), "自定义 Skills", BLUE)
    metric(draw, (630, 220, 870, 352), str(system_count), "系统 Skills 副本", GREEN)
    metric(draw, (790, 404, 1030, 536), "8+", "主要能力方向", YELLOW)

    rounded_box(draw, (70, 404, 730, 566), fill=CARD, outline=LINE, width=1)
    write(draw, (98, 432), "覆盖方向", SECTION_FONT)
    lines = [
        "信息整理：article-summary / conversation-html-summary / summarize-current-conversation / optimize-prompt",
        "内容抓取：daily-ai-news / bilibili-video-summary / speech-to-text",
        "文档办公：markdown-converter / docx / pdf / pptx / xlsx",
        "工程协作：code-review-cr / harness-engineering / webapp-testing / web-design-guidelines",
        "平台与自动化：agent-browser / azure-cost / microsoft-foundry / ue-doc-to-video",
    ]
    y = 476
    for line in lines:
        draw.ellipse((100, y + 3, 112, y + 15), fill=BLUE)
        write(draw, (128, y), line, SMALL_FONT, TEXT)
        y += 26
    return image


def build_frame_workflow() -> Image.Image:
    image = draw_background()
    draw = ImageDraw.Draw(image)
    header(draw, "GitHub 首页 30 秒看懂")

    steps = [
        ("1", "选择 Skill", "按任务匹配目录中的 SKILL.md"),
        ("2", "下达请求", "在 Codex 中用自然语言触发"),
        ("3", "生成产物", "输出脚本、文档、页面、数据或素材"),
        ("4", "回收沉淀", "把新规则、模板和脚本继续提交回仓库"),
    ]

    x = 70
    for index, (number, title, body) in enumerate(steps):
        accent = PURPLE if index in (0, 3) else BLUE if index == 1 else GREEN
        rounded_box(draw, (x, 234, x + 220, 404), fill=CARD, outline=accent, width=2)
        write(draw, (x + 28, 260), number, TITLE_FONT, accent)
        write(draw, (x + 86, 258), title, SECTION_FONT)
        multiline(draw, (x + 28, 316), body, SMALL_FONT, TEXT_MUTED, spacing=7)
        if index < len(steps) - 1:
            draw.line((x + 220, 319, x + 244, 319), fill=(150, 164, 197), width=4)
            draw.polygon([(x + 244, 319), (x + 232, 311), (x + 232, 327)], fill=(150, 164, 197))
        x += 250

    code_panel(
        draw,
        (70, 456, 1030, 558),
        "Prompt Example",
        "使用 $daily-ai-news 汇总今天的 AI 资讯，并按官方 / 开源 / 社区输出中文日报",
    )
    return image


def build_frame_readme() -> Image.Image:
    image = draw_background()
    draw = ImageDraw.Draw(image)
    header(draw, "README 开源项目标准化")

    rounded_box(draw, (70, 214, 1030, 542), fill=CARD, outline=LINE, width=1)
    write(draw, (100, 246), "README 应该让访问者快速理解什么？", SUBTITLE_FONT)

    points = [
        "项目定位：这是一个管理和同步本地 Skills 的仓库，不是单个脚本合集",
        "演示素材：顶部 GIF 先展示价值，再引导读者看安装和使用方式",
        "技能索引：按类别列出核心 Skills，让访问者快速找到能力入口",
        "目录规范：说明 SKILL.md / references / scripts / assets 的职责",
        "开源协作：补齐贡献方式、路线图、许可说明和后续扩展方向",
    ]
    y = 312
    for point in points:
        draw.ellipse((102, y + 5, 116, y + 19), fill=GREEN)
        write(draw, (136, y), point, TEXT_FONT, TEXT)
        y += 46

    write(draw, (100, 578), "把本地 skills 目录打磨成一个可维护、可展示、可协作的开源项目。", SECTION_FONT)
    return image


def save_assets(write_preview: bool = False) -> None:
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    frames = [
        build_frame_overview(),
        build_frame_catalog(),
        build_frame_workflow(),
        build_frame_readme(),
    ]
    frames[0].save(
        GIF_PATH,
        save_all=True,
        append_images=frames[1:],
        duration=[1300, 1300, 1300, 1500],
        loop=0,
        optimize=True,
        disposal=2,
    )
    if write_preview:
        frames[0].save(PREVIEW_PATH)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate the README demo GIF for the repository homepage.")
    parser.add_argument("--preview", action="store_true", help="Also export the first frame as a PNG preview.")
    args = parser.parse_args()

    save_assets(write_preview=args.preview)
    print(GIF_PATH)
    if args.preview:
        print(PREVIEW_PATH)
