"""Replace host-specific dashboard values with explicit demo data."""
from argparse import ArgumentParser
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def sanitize(source: Path, target: Path, language: str = "zh") -> None:
    image = Image.open(source).convert("RGB")
    draw = ImageDraw.Draw(image)
    if language == "en":
        regular = ImageFont.truetype(r"C:\Windows\Fonts\segoeui.ttf", 13)
        bold = ImageFont.truetype(r"C:\Windows\Fonts\segoeuib.ttf", 15)
        small = ImageFont.truetype(r"C:\Windows\Fonts\segoeui.ttf", 11)
        panel = (670, 277, 1265, 573)
        title = "System info"
        badge = "DEMO DATA"
        rows = [
            ("OS", "Windows 11 (Demo)"),
            ("Architecture", "64-bit (AMD64)"),
            ("Hostname", "GENBOX-DEMO"),
            ("Python", "3.12.10"),
            ("Uptime", "2h 35m"),
            ("Disk space", "120.0 GB available / 256.0 GB"),
            ("Disk usage", "53.1%"),
            ("Gallery", "24 images | 48.2 MB"),
            ("Video history", "6 videos | 120.0 MB"),
        ]
        draw.rounded_rectangle((88, 99, 1265, 136), radius=8, fill=(248, 249, 251), outline=(225, 229, 235), width=1)
        draw.text((104, 110), "Demo capture - external connectivity checks omitted", font=small, fill=(91, 99, 111))
        draw.rounded_rectangle((670, 599, 1265, 735), radius=15, fill=(248, 249, 251), outline=(225, 229, 235), width=1)
        draw.text((688, 619), "Local IP info", font=bold, fill=(25, 32, 42))
        draw.rounded_rectangle((1164, 616, 1248, 640), radius=5, fill=(229, 244, 255))
        draw.text((1174, 620), "DEMO DATA", font=small, fill=(24, 116, 176))
        draw.text((688, 659), "Example address", font=regular, fill=(91, 99, 111))
        draw.text((1158, 659), "192.0.2.10", font=regular, fill=(29, 35, 44))
        draw.text((688, 688), "Private network", font=regular, fill=(91, 99, 111))
        draw.text((1154, 688), "Not connected", font=regular, fill=(29, 35, 44))
    else:
        regular = ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 13)
        bold = ImageFont.truetype(r"C:\Windows\Fonts\msyhbd.ttc", 15)
        small = ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 11)
        panel = (752, 277, 1402, 571)
        title = "系统信息"
        badge = "演示数据"
        rows = [
            ("操作系统", "Windows 11 (Demo)"),
            ("架构", "64-bit (AMD64)"),
            ("主机名", "GENBOX-DEMO"),
            ("Python", "3.12.10"),
            ("运行时间", "2h 35m"),
            ("磁盘空间", "120.0 GB 可用 / 256.0 GB"),
            ("磁盘占用", "53.1%"),
            ("图库", "24 张图片 | 48.2 MB"),
            ("视频库", "6 个视频 | 120.0 MB"),
        ]

    draw.rounded_rectangle(panel, radius=15, fill=(248, 249, 251), outline=(225, 229, 235), width=1)
    left, top, right, _ = panel
    draw.text((left + 16, top + 20), title, font=bold, fill=(25, 32, 42))
    badge_box = draw.textbbox((0, 0), badge, font=small)
    badge_width = badge_box[2] - badge_box[0] + 20
    draw.rounded_rectangle((right - badge_width - 16, top + 17, right - 16, top + 41), radius=5, fill=(229, 244, 255))
    draw.text((right - badge_width - 6, top + 21), badge, font=small, fill=(24, 116, 176))

    y = 328
    for label, value in rows:
        draw.line((left + 16, y + 25, right - 17, y + 25), fill=(220, 224, 230), width=1)
        draw.text((left + 16, y + 5), label, font=regular, fill=(91, 99, 111))
        value_box = draw.textbbox((0, 0), value, font=regular)
        draw.text((right - 17 - (value_box[2] - value_box[0]), y + 5), value, font=regular, fill=(29, 35, 44))
        y += 27

    target.parent.mkdir(parents=True, exist_ok=True)
    image.save(target, optimize=True)


def main() -> None:
    parser = ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("target", type=Path)
    parser.add_argument("--language", choices=("zh", "en"), default="zh")
    args = parser.parse_args()
    sanitize(args.source, args.target, args.language)


if __name__ == "__main__":
    main()
