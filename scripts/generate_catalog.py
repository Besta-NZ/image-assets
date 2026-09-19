#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate_catalog.py
===================
扫描 images/ 下的原图与 thumbs/ 下的缩略图，生成根目录 catalog.json。

依赖：Pillow（pip install Pillow）

⚠️ 使用前请替换下面 BASE_URL 的占位符为你的实际 CDN / GitHub Pages 地址。
   例如使用 jsDelivr：https://cdn.jsdelivr.net/gh/<你的用户名>/<仓库名>@main/
   例如使用 GitHub Pages：https://<你的用户名>.github.io/<仓库名>/
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    sys.stderr.write(
        "错误：未安装 Pillow，请先运行 `pip install Pillow`。\n"
    )
    sys.exit(1)

# ============================================================
# ⚠️ 请替换为你的实际静态资源根地址（末尾保留斜杠 /）
# 示例(jsDelivr): https://cdn.jsdelivr.net/gh/GitHub用户名/仓库名@main/
# 示例(GitHub Pages): https://GitHub用户名.github.io/仓库名/
# ============================================================
BASE_URL = "https://cdn.jsdelivr.net/gh/Besta-NZ/image-assets@main/"

# 脚本所在目录的上一级 = 仓库根目录
ROOT = Path(__file__).resolve().parent.parent
IMAGES_DIR = ROOT / "images"
THUMBS_DIR = ROOT / "thumbs"
OUTPUT_FILE = ROOT / "catalog.json"

SUPPORTED_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
THUMB_FALLBACK_EXT = ".jpg"


def find_thumb(image_file: Path) -> Path | None:
    """根据原图文件名（不含扩展名）在 thumbs/ 中查找缩略图。
    优先同名同格式，其次同名 .jpg。找不到返回 None。"""
    stem = image_file.stem
    # 1. 同名同格式
    candidate = THUMBS_DIR / (stem + image_file.suffix.lower())
    if candidate.exists():
        return candidate
    # 2. 同名 + .jpg
    candidate = THUMBS_DIR / (stem + THUMB_FALLBACK_EXT)
    if candidate.exists():
        return candidate
    return None


def build_catalog() -> dict:
    images: list[dict] = []

    if not IMAGES_DIR.exists():
        print(f"[WARN] images/ 目录不存在：{IMAGES_DIR}")
        return {"images": []}

    files = [
        f for f in IMAGES_DIR.iterdir()
        if f.is_file() and f.suffix.lower() in SUPPORTED_EXTS
    ]

    for image_file in sorted(files, key=lambda p: p.stem.lower()):
        thumb = find_thumb(image_file)
        if thumb is None:
            print(f"[WARN] 找不到缩略图，跳过：{image_file.name}")
            continue

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

    # 按 id 排序
    images.sort(key=lambda item: item["id"].lower())
    return {"images": images}


def main() -> None:
    catalog = build_catalog()

    # version 用毫秒时间戳，保证每次运行都不同
    catalog["version"] = str(int(time.time() * 1000))
    catalog["updated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    catalog["base_url"] = BASE_URL
    # 确保字段顺序固定：base_url 放前面，images 在最后
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
