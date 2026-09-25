#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate_catalog.py
===================
扫描 images/ 下的原图 → 自动生成/匹配 thumbs/ 缩略图 → 生成根目录 catalog.json。

依赖：Pillow（pip install Pillow）

新增：找不到缩略图时自动生成（等比缩放到 THUMB_WIDTH，统一存 .jpg）。
      已存在的缩略图默认**保留不覆盖**；加 --force 才重生成。

⚠️ 使用前请替换下面 BASE_URL 为实际 CDN / GitHub Pages 地址。
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    sys.stderr.write("错误：未安装 Pillow，请先运行 `pip install Pillow`。\n")
    sys.exit(1)

# ============================================================
# ⚠️ 请替换为你的实际静态资源根地址（末尾保留斜杠 /）
# 示例(jsDelivr): https://cdn.jsdelivr.net/gh/GitHub用户名/仓库名@main/
# 示例(GitHub Pages): https://GitHub用户名.github.io/仓库名/
# ============================================================
BASE_URL = "https://cdn.jsdelivr.net/gh/Besta-NZ/image-assets@latest/"

# 脚本所在目录的上一级 = 仓库根目录
ROOT = Path(__file__).resolve().parent.parent
IMAGES_DIR = ROOT / "images"
THUMBS_DIR = ROOT / "thumbs"
OUTPUT_FILE = ROOT / "catalog.json"

SUPPORTED_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
THUMB_FALLBACK_EXT = ".jpg"


def generate_thumb(image_file: Path, out_dir: Path, width: int) -> Path:
    """从原图生成等比缩略图，输出为同名 .jpg。"""
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / (image_file.stem + THUMB_FALLBACK_EXT)
    with Image.open(image_file) as im:
        im.thumbnail((width, width))
        im.convert("RGB").save(target, format="JPEG", quality=85, optimize=True)
    return target


def find_thumb(image_file: Path) -> Path | None:
    """根据原图文件名（不含扩展名）在 thumbs/ 中查找缩略图。
    优先同名同格式，其次同名 .jpg。找不到返回 None。"""
    stem = image_file.stem
    for ext in (image_file.suffix.lower(), THUMB_FALLBACK_EXT):
        candidate = THUMBS_DIR / (stem + ext)
        if candidate.exists():
            return candidate
    return None


def build_catalog(thumb_width: int, force_thumb: bool) -> dict:
    images: list[dict] = []

    if not IMAGES_DIR.exists():
        print(f"[WARN] images/ 目录不存在：{IMAGES_DIR}")
        return {"images": []}

    THUMBS_DIR.mkdir(parents=True, exist_ok=True)

    files = [
        f for f in IMAGES_DIR.iterdir()
        if f.is_file() and f.suffix.lower() in SUPPORTED_EXTS
    ]

    for image_file in sorted(files, key=lambda p: p.stem.lower()):
        thumb = find_thumb(image_file)
        if thumb is None:
            thumb = generate_thumb(image_file, THUMBS_DIR, thumb_width)
            print(f"[AUTO] 生成缩略图：{image_file.name} → {thumb.relative_to(ROOT)}")
        elif force_thumb:
            thumb = generate_thumb(image_file, THUMBS_DIR, thumb_width)
            print(f"[OVERRIDE] 重生成缩略图：{thumb.name}")
        else:
            print(f"[KEEP] 复用已有缩略图：{thumb.name}")

        try:
            with Image.open(image_file) as im:
                width, height = im.size
        except Exception as e:
            print(f"[WARN] 无法读取原图尺寸，跳过：{image_file.name}（{e}）")
            continue

        images.append({
            "id": image_file.stem,
            "name": image_file.stem,
            "category": "default",
            "thumb": f"thumbs/{thumb.name}",
            "image": f"images/{image_file.name}",
            "width": width,
            "height": height,
        })

    images.sort(key=lambda item: item["id"].lower())
    return {"images": images}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="扫描 images/、自动生成 thumbs/、输出 catalog.json")
    p.add_argument("--thumb-width", type=int, default=400,
                   help="自动生成缩略图的目标宽度（等比缩放），默认 400")
    p.add_argument("--force", action="store_true",
                   help="覆盖已有的缩略图并重新生成（默认保留已有）")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    catalog = build_catalog(thumb_width=args.thumb_width, force_thumb=args.force)

    catalog["version"] = str(int(time.time() * 1000))
    catalog["updated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    catalog["base_url"] = BASE_URL
    ordered = {
        "version": catalog["version"],
        "updated_at": catalog["updated_at"],
        "base_url": catalog["base_url"],
        "images": catalog["images"],
    }

    OUTPUT_FILE.write_text(
        json.dumps(ordered, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"[OK] 已生成 {OUTPUT_FILE}，共 {len(ordered['images'])} 张图片。")


if __name__ == "__main__":
    main()
