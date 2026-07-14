"""Replace host-specific dashboard values with explicit demo data."""
from argparse import ArgumentParser
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def sanitize(source: Path, target: Path) -> None:
    image = Image.open(source).convert("RGB")
    draw = ImageDraw.Draw(image)
    regular = ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 13)
    bold = ImageFont.truetype(r"C:\Windows\Fonts\msyhbd.ttc", 15)
    small = ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 11)

    panel = (752, 277, 1402, 571)
    draw.rounded_rectangle(panel, radius=15, fill=(248, 249, 251), outline=(225, 229, 235), width=1)
    draw.text((768, 297), "系统信息", font=bold, fill=(25, 32, 42))
    draw.rounded_rectangle((1315, 294, 1385, 318), radius=5, fill=(229, 244, 255))
    draw.text((1327, 298), "演示数据", font=small, fill=(24, 116, 176))

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
    y = 328
    for label, value in rows:
        draw.line((768, y + 25, 1385, y + 25), fill=(220, 224, 230), width=1)
        draw.text((768, y + 5), label, font=regular, fill=(91, 99, 111))
        value_box = draw.textbbox((0, 0), value, font=regular)
        draw.text((1385 - (value_box[2] - value_box[0]), y + 5), value, font=regular, fill=(29, 35, 44))
        y += 27

    target.parent.mkdir(parents=True, exist_ok=True)
    image.save(target, optimize=True)


def main() -> None:
    parser = ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("target", type=Path)
    args = parser.parse_args()
    sanitize(args.source, args.target)


if __name__ == "__main__":
    main()
