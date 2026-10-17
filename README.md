# Image Assets

拼图 App（Puzzle Master）在线图库的**静态图片目录**，以只读方式被 App 拉取（GitHub Pages 实时清单 + jsDelivr CDN 加速）。

## 目录结构

```
.
├── images/                      # 图库原图（App 下载后裁剪为拼图素材）
├── thumbs/                      # 缩略图（sync.py 自动生成，勿手工维护）
├── backgrounds/                 # 主界面背景源图（四季海滨城市套图）
├── backgrounds_opt/             # 背景优化产物（sync.py 生成）
├── categories.json              # 图库分类映射（id → 分类），见「分类规则」
├── scripts/sync.py              # 一键同步：缩略图/分类/catalog/git 推送
├── .github/workflows/
│   └── update_catalog.yml       # Push 到 main 时自动重建 catalog.json
├── .nojekyll                    # 禁用 GitHub Pages 的 Jekyll 构建
└── catalog.json                 # 图片清单（自动生成，勿手改）
```

## 素材规格规则（自动化生产必读）

### 1. 在线图库图 `images/`

| 规则项 | 要求 |
|---|---|
| 格式 | JPEG（`.jpg` / `.jpeg`）；PNG 源文件须先转 JPEG |
| 尺寸 | 1080 × 1080（正方形，最长边 ≤1440px） |
| 文件大小 | ≤ 500 KB |
| 色彩 | RGB（不含 alpha 通道） |
| 命名 | 见「命名规则」 |

> 上限口径与 App 内置图库一致：最长边 ≤1440px、≤500KB。1080×1080 是当前 60 张图的实测基准。

### 2. 缩略图 `thumbs/`

- **无需手工制作**：`sync.py` 自动生成（宽 400px、JPEG quality=85、optimize）
- 删除原图时自动清理对应孤儿缩略图

### 3. 主界面背景 `backgrounds/`

| 规则项 | 要求 |
|---|---|
| 格式 | JPEG |
| 尺寸 | 竖版，最长边 ≤1440px（当前套图为 816×1440） |
| 文件大小 | ≤ 500 KB（优化后参考 200~255KB） |
| 内容 | 四季海滨城市插画，**自带 "Puzzle Master" Logo 居中偏上**，周边留白供覆盖元素 |
| 命名 | `bg_theme_N.jpg`（N 从 1 递增，**勿删改中间序号**——App 按日轮换 `dayId % N`，删除会错位） |

源图放入 `backgrounds/` 后由 `sync.py` 生成 `backgrounds_opt/` 优化版，再复制到 App 的 `drawable-nodpi/` 作离线兜底。

### 4. Splash 启动背景 `splash_bg.jpg`（App 内置，非本仓库）

竖版 ≤1440px、JPEG ≤500KB、Logo 居中偏上、**下方 1/4 留白**（进度条区域）。

## 命名规则

| 场景 | 格式 | 示例 |
|---|---|---|
| 图库图（无分类前缀，走映射表） | 3 位流水号 | `061.jpg` |
| 图库图（**分类前缀，推荐**，免登记） | `<分类>_<名称>` | `animals_tiger.jpg`、`flowers_rose.jpg` |
| 主界面背景 | `bg_theme_N` | `bg_theme_5.jpg` |

- 仅允许**小写字母、数字、下划线**（ hyphen `-` 亦可作前缀分隔）
- id 取文件名去扩展名，直接决定 CDN URL 与 catalog 条目——**已发布的 id 永不重命名**（会导致已下载用户数据失效）

## 分类规则

分类解析优先级（`sync.py`）：

```
categories.json 显式映射  >  文件名前缀（animals_xxx → animals）  >  other 兜底 + WARN
```

- 有效分类（7 个，与 App 端 `cat_*` 本地化 key 一一对应）：
  `animals` `flowers` `nature` `cartoon` `food` `city` `other`
- 新增图片**推荐**用分类前缀命名，免登记；用流水号命名则须在 `categories.json` 补一行
- **新增分类**需 App 发版补 11 语言翻译（未收录分类旧版本回退显示英文原文，不阻塞）

## 工作流程

```bash
# 新增图片后一键同步（生成缩略图 + catalog + git 推送）
python scripts/sync.py -m "feat: add images"

# 仅更新分类映射后重新生成 catalog
python scripts/sync.py
```

1. 图片放入 `images/`（命名带分类前缀，或在 `categories.json` 登记）
2. 运行 `sync.py`：自动生成缩略图、按优先级归类、重建 `catalog.json`、commit + pull --rebase + push
3. App 端下次启动经 Splash 拉取新 catalog（jsDelivr `@latest` 有分钟级缓存延迟）

## 注意

- `catalog.json` 由脚本自动生成，勿手工编辑
- 生产新图请对照「素材规格规则」逐项自检：JPEG / 尺寸 / ≤500KB / RGB / 命名
- jsDelivr 在部分网络（IPv6 优先环境）不可达——为已知环境限制，真机正常网络无碍
