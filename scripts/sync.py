#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sync.py
=======
图片库一键同步推送脚本（增 / 删 / 改 统一处理 + 推送 GitHub）。

能力：
  1. 新增原图      → 自动生成缩略图
  2. 替换原图      → 通过 mtime 识别 → 自动重生成对应缩略图（保持新原图与新缩略图一致）
  3. 删除原图      → 自动清理 thumbs/ 中的孤儿缩略图
  4. 重写          → catalog.json
  5. git 流程      → add → commit（自动生成 message）→ pull --rebase → 冲突自动重跑 → push
  6. 安全检查      → 进入前确认仓库不在 rebase / merge 进行中

用法：
    py scripts\\sync.py                       # 全流程：同步图片 + 推送
    py scripts\\sync.py -m "feat: 添加 022"   # 自定义 commit message
    py scripts\\sync.py --force               # 强制重生成所有缩略图
    py scripts\\sync.py --dry-run             # 只跑图片处理，不做 git 操作
    py scripts\\sync.py --no-push             # 跑图片 + commit + rebase，但不 push

依赖：Pillow（pip install Pillow）
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
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
# 配置
# ============================================================
BASE_URL = "https://cdn.jsdelivr.net/gh/Besta-NZ/image-assets@latest/"

# 脚本所在目录的上一级 = 仓库根目录
ROOT = Path(__file__).resolve().parent.parent
IMAGES_DIR = ROOT / "images"
THUMBS_DIR = ROOT / "thumbs"
OUTPUT_FILE = ROOT / "catalog.json"

SUPPORTED_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
THUMB_FALLBACK_EXT = ".jpg"
DEFAULT_THUMB_WIDTH = 400


# ============================================================
# 图片处理
# ============================================================
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


def is_thumb_stale(image_file: Path, thumb_file: Path) -> bool:
    """判断缩略图是否过期：原图 mtime 比缩略图新 → 过期（用于检测替换）。

    替换原图时，新文件的 mtime 通常会更新，因此能识别为"替换"。
    若用户用 `cp --no-preserve=times` 等方式保留旧 mtime，则需用 --force 强制重生成。
    """
    return image_file.stat().st_mtime > thumb_file.stat().st_mtime


def sync_thumbnails(thumb_width: int, force: bool) -> dict:
    """同步缩略图：新增 / 替换 / 保留 / 清理孤儿。返回统计信息。"""
    stats = {"added": 0, "replaced": 0, "kept": 0, "orphans_removed": 0}

    if not IMAGES_DIR.exists():
        print(f"[WARN] images/ 目录不存在：{IMAGES_DIR}")
        return stats

    THUMBS_DIR.mkdir(parents=True, exist_ok=True)

    # 1. 扫描所有原图，决定每张缩略图的动作
    files = [
        f for f in IMAGES_DIR.iterdir()
        if f.is_file() and f.suffix.lower() in SUPPORTED_EXTS
    ]

    valid_stems: set[str] = set()  # 用于孤儿检测

    for image_file in sorted(files, key=lambda p: p.stem.lower()):
        valid_stems.add(image_file.stem)
        thumb = find_thumb(image_file)

        if thumb is None:
            # 新增：原图无缩略图 → 生成
            thumb = generate_thumb(image_file, THUMBS_DIR, thumb_width)
            print(f"[ADD]     生成缩略图：{image_file.name} → {thumb.relative_to(ROOT)}")
            stats["added"] += 1
        elif force:
            # --force：无脑重生成
            thumb = generate_thumb(image_file, THUMBS_DIR, thumb_width)
            print(f"[FORCE]   重生成缩略图：{thumb.name}")
            stats["replaced"] += 1
        elif is_thumb_stale(image_file, thumb):
            # 替换：原图 mtime 比缩略图新 → 重生成（保持新原图与新缩略图一致）
            thumb = generate_thumb(image_file, THUMBS_DIR, thumb_width)
            print(f"[REPLACE] 重生成缩略图：{thumb.name}（原图已更新）")
            stats["replaced"] += 1
        else:
            # 保留：原图与缩略图同步
            print(f"[KEEP]    复用已有缩略图：{thumb.name}")
            stats["kept"] += 1

    # 2. 清理孤儿缩略图：thumbs/ 中没有对应原图的文件
    for thumb in THUMBS_DIR.iterdir():
        if not thumb.is_file():
            continue
        if thumb.suffix.lower() not in SUPPORTED_EXTS and thumb.suffix.lower() != ".jpg":
            continue
        if thumb.stem not in valid_stems:
            try:
                thumb.unlink()
                print(f"[DEL]     清理孤儿缩略图：{thumb.name}")
                stats["orphans_removed"] += 1
            except OSError as e:
                print(f"[WARN]    无法删除孤儿缩略图：{thumb.name}（{e}）")

    return stats


def build_catalog() -> list[dict]:
    """构建 catalog 的 images 数组。"""
    images: list[dict] = []

    if not IMAGES_DIR.exists():
        return images

    files = [
        f for f in IMAGES_DIR.iterdir()
        if f.is_file() and f.suffix.lower() in SUPPORTED_EXTS
    ]

    for image_file in sorted(files, key=lambda p: p.stem.lower()):
        thumb = find_thumb(image_file)
        if thumb is None:
            print(f"[WARN] 缩略图缺失，跳过：{image_file.name}")
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

    return images


def write_catalog(images: list[dict]) -> None:
    """写 catalog.json。"""
    catalog = {
        "version": str(int(time.time() * 1000)),
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "base_url": BASE_URL,
        "images": images,
    }
    OUTPUT_FILE.write_text(
        json.dumps(catalog, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"[OK] 已写 catalog.json，共 {len(images)} 张图片。")


# ============================================================
# Git 操作
# ============================================================
def git(*args: str, check: bool = True, capture: bool = True) -> subprocess.CompletedProcess:
    """运行 git 命令（capture=True 时捕获输出，否则直通终端）。"""
    cmd = ["git", "-C", str(ROOT), *args]
    result = subprocess.run(
        cmd,
        capture_output=capture,
        text=True,
        encoding="utf-8",
    )
    if check and result.returncode != 0:
        print(f"[GIT ERROR] {' '.join(cmd)}")
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr)
        raise RuntimeError("git command failed")
    return result


def check_clean_state() -> None:
    """检查仓库是否处于干净状态（不在 rebase / merge 中）。"""
    git_dir = ROOT / ".git"
    rebase_merge = git_dir / "rebase-merge"
    rebase_apply = git_dir / "rebase-apply"
    merge_head = git_dir / "MERGE_HEAD"

    if rebase_merge.exists() or rebase_apply.exists():
        print("[ERROR] 仓库正处于 rebase 进行中状态，无法继续。")
        print(f"        请先运行：git -C \"{ROOT}\" rebase --abort")
        sys.exit(1)

    if merge_head.exists():
        print("[ERROR] 仓库正处于 merge 进行中状态，无法继续。")
        print(f"        请先运行：git -C \"{ROOT}\" merge --abort")
        sys.exit(1)


def git_status_porcelain() -> str:
    """获取 git status --porcelain 输出。"""
    return git("status", "--porcelain").stdout


def has_changes() -> bool:
    """检查工作区是否有任何变更。"""
    return bool(git_status_porcelain().strip())


def build_commit_message(stats: dict, custom_msg: str | None) -> str:
    """根据变更统计构建 commit message。"""
    if custom_msg:
        return custom_msg

    parts: list[str] = []
    if stats["added"]:
        parts.append(f"+{stats['added']} new")
    if stats["replaced"]:
        parts.append(f"~{stats['replaced']} replaced")
    if stats["orphans_removed"]:
        parts.append(f"-{stats['orphans_removed']} removed")

    if not parts:
        return "chore: regenerate catalog.json"

    return f"chore: sync images ({', '.join(parts)})"


def git_stage_all() -> None:
    """暂存 images/ thumbs/ catalog.json（Git 2.0+ 用目录会包含删除）。"""
    git("add", "images/", "thumbs/", "catalog.json")


def git_commit(message: str) -> bool:
    """提交。返回是否真的提交了（无变更返回 False）。"""
    result = git("commit", "-m", message, check=False)
    out = (result.stdout or "") + (result.stderr or "")
    if result.returncode != 0:
        if "nothing to commit" in out:
            return False
        print(f"[GIT ERROR] commit failed:\n{out}")
        raise RuntimeError("git commit failed")
    return True


def git_pull_rebase() -> bool:
    """pull --rebase。返回 True 表示无需处理，False 表示有 catalog.json 冲突需重跑。"""
    result = git("pull", "--rebase", "origin", "main", check=False, capture=True)
    output = (result.stdout or "") + (result.stderr or "")

    if result.returncode == 0:
        # 成功（fast-forward / 已是最新 / 成功 rebase）
        last_line = output.strip().splitlines()[-1] if output.strip() else "up to date"
        print(f"[GIT] pull --rebase: {last_line}")
        return True

    # 检查是否是 catalog.json 冲突（可自动解决）
    if "CONFLICT" in output and "catalog.json" in output:
        print("[GIT] catalog.json 冲突，自动重跑脚本解决...")
        return False

    # 其他类型冲突，抛错让用户手动处理
    print(f"[GIT ERROR] 无法自动解决的冲突：\n{output}")
    print("[HINT] 请手动处理后再次运行本脚本")
    raise RuntimeError("unresolved git conflict")


def git_resolve_conflict_and_continue(thumb_width: int) -> None:
    """解决 catalog.json 冲突并继续 rebase。"""
    # 1. 用 theirs（远程版本）覆盖 catalog.json
    git("checkout", "--theirs", "catalog.json", check=False)

    # 2. 重跑脚本生成最新 catalog（同时确保 thumbs 也同步）
    print("[GIT] 重跑图片同步以解决冲突...")
    sync_thumbnails(thumb_width=thumb_width, force=False)
    images = build_catalog()
    write_catalog(images)

    # 3. 标记冲突已解决
    git("add", "catalog.json")

    # 4. 继续 rebase（设置 GIT_EDITOR=true 避免交互式编辑器弹窗）
    env = os.environ.copy()
    env["GIT_EDITOR"] = "true"

    cmd = ["git", "-C", str(ROOT), "rebase", "--continue"]
    result = subprocess.run(cmd, capture_output=True, text=True, env=env, encoding="utf-8")

    if result.returncode != 0:
        output = (result.stdout or "") + (result.stderr or "")
        print(f"[GIT ERROR] rebase --continue 失败：\n{output}")
        print(f"[HINT] 请手动运行：git -C \"{ROOT}\" rebase --abort 退出")
        raise RuntimeError("rebase --continue failed")

    print("[GIT] rebase 完成")


def git_push() -> bool:
    """push 到 origin main。"""
    result = git("push", "origin", "main", check=False)
    if result.returncode == 0:
        for line in (result.stdout or "").splitlines():
            if "->" in line or "main" in line:
                print(f"[GIT] {line.strip()}")
        return True
    print(f"[GIT ERROR] push 失败：\n{result.stdout}\n{result.stderr}")
    return False


# ============================================================
# 主流程
# ============================================================
def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="图片库一键同步推送脚本（增/删/改统一处理）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("-m", "--message", type=str, default=None,
                   help="自定义 commit message（默认根据变更自动生成）")
    p.add_argument("--thumb-width", type=int, default=DEFAULT_THUMB_WIDTH,
                   help=f"缩略图宽度，默认 {DEFAULT_THUMB_WIDTH}")
    p.add_argument("--force", action="store_true",
                   help="强制重生成所有缩略图（默认只重生成新图和被替换的图）")
    p.add_argument("--dry-run", action="store_true",
                   help="只跑图片处理，不做 git 操作")
    p.add_argument("--no-push", action="store_true",
                   help="跑图片处理 + commit + pull rebase，但不 push")
    return p.parse_args()


def main() -> None:
    args = parse_args()

    print("=" * 60)
    print("图片库同步脚本（增/删/改统一处理 + 推送 GitHub）")
    print(f"仓库路径：{ROOT}")
    print("=" * 60)

    # 0. 安全检查：仓库必须处于干净状态
    print("\n[0/5] 检查仓库状态...")
    check_clean_state()
    print("  OK")

    # 1. 同步缩略图（新增 / 替换 / 清理孤儿）
    print("\n[1/5] 同步缩略图...")
    stats = sync_thumbnails(thumb_width=args.thumb_width, force=args.force)
    print(f"  新增：{stats['added']}，替换：{stats['replaced']}，"
          f"保留：{stats['kept']}，孤儿清理：{stats['orphans_removed']}")

    # 2. 生成 catalog.json
    print("\n[2/5] 生成 catalog.json...")
    images = build_catalog()
    write_catalog(images)

    if args.dry_run:
        print("\n[--dry-run] 不执行 git 操作。")
        return

    # 3. 检查变更
    print("\n[3/5] 检查 git 变更...")
    if not has_changes():
        print("  无变更，结束。")
        return

    # 4. 暂存 + 提交
    print("\n[4/5] 提交变更...")
    git_stage_all()
    msg = build_commit_message(stats, args.message)
    print(f"  commit: {msg}")
    if not git_commit(msg):
        print("  无变更可提交。")
        return

    # 5. pull rebase + push
    print("\n[5/5] 同步远程...")
    if not git_pull_rebase():
        git_resolve_conflict_and_continue(thumb_width=args.thumb_width)

    if args.no_push:
        print("\n[--no-push] 不执行推送。")
        return

    if git_push():
        print("\n[OK] 同步完成！")
    else:
        print("\n[FAIL] 推送失败，请手动处理。")
        sys.exit(1)


if __name__ == "__main__":
    main()
