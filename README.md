# Image Assets

拼图 App 在线图库的**静态图片目录**，以**只读方式**被 App 拉取。

## 目录结构

```
.
├── images/                      # 原图（App 下载到本地后裁剪使用）
├── thumbs/                      # 缩略图（与原图同名，用于列表预览）
├── scripts/generate_catalog.py  # 扫描图片并生成 catalog.json
├── .github/workflows/
│   └── update_catalog.yml       # Push 到 main 时自动重建 catalog.json
├── .nojekyll                    # 禁用 GitHub Pages 的 Jekyll 构建
└── catalog.json                 # 图片清单（由脚本自动生成，勿手改）
```

## 工作流程

1. 往 `images/` 放原图，往 `thumbs/` 放**同名**缩略图（优先同格式，无则用 `.jpg`）。
2. 本地运行 `python scripts/generate_catalog.py` 可手动生成 `catalog.json`。
3. 推送到 `main` 分支后，GitHub Actions 会自动重新生成并提交 `catalog.json`。
4. App 通过 CDN / GitHub Pages 拉取 `catalog.json`，按需下载 `thumbs/` 与 `images/`。

## 注意

- **使用前**必须把 `scripts/generate_catalog.py` 中的 `BASE_URL` 替换为你的实际 CDN 地址。
- `catalog.json` 由脚本自动生成，请勿手工编辑。
