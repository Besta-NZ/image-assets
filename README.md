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

## 新增图片操作流程（完整）

### Step 1：放图片

将 JPEG 文件直接放入 `images/` **根目录**（脚本只扫一级，子文件夹不会被处理）。命名带分类前缀最省心（如 `flowers_daisy.jpg`、`nature_waterfall.jpg`），免登记自动归类。

> ⚠️ **不要在现有 001-060 中间插入改名**——catalog.json 的 `id` 就是文件名 stem，App 端玩家进度按 id 存，改序号会错位。

### Step 2：（可选）在 `categories.json` 登记分类

如果用流水号命名或想显式指定分类，加一行即可：

```json
{
  "061": "nature",
  "flowers_rose": "flowers"
}
```

分类解析优先级：`categories.json 显式映射` > `文件名前缀` > `other 兜底 + WARN`。

### Step 3：运行 sync.py（全自动，不需要传文件名或数量）

> ⚠️ 本机必须用 `py` 启动器，**不要用 `python`**：本机 `python` 指向微软商店占位别名
> （`C:\Users\zhou\AppData\Local\Microsoft\WindowsApps\python.exe`），执行时无任何输出并
> 返回退出码 9009，脚本根本没跑起来。验证：`py --version` 应输出 Python 3.12.3。

```bash
# 最简用法：自动扫描 images/，变了什么就处理什么
py scripts/sync.py

# 自定义 commit message
py scripts/sync.py -m "feat: add 5 new flower images"

# 预演（只生成缩略图 + catalog，不碰 git）—— 第一次跑或改命名规则时推荐先 dry-run
py scripts/sync.py --dry-run

# 替换时文件 mtime 没变导致脚本没识别出来 → 强制重生成所有缩略图
py scripts/sync.py --force

# commit 了但暂时不想 push
py scripts/sync.py --no-push
```

### sync.py 做了什么

```
images/ 扫描
  ├── 新增文件   → 生成缩略图 + catalog 新增条目
  ├── 同文件名覆盖 → 检测原图 mtime 比缩略图新 → 重生成缩略图 + catalog 更新条目
  └── 删除文件   → thumbs/ 孤儿清理 + catalog 移除条目
      ↓
catalog.json 重写（含原图路径、缩略图路径、尺寸、分类）
      ↓
git add images/ thumbs/ catalog.json categories.json
      ↓
commit → pull --rebase（自动解决 catalog.json 冲突）→ push
```

App 端**无需重新发版**——在线图库模块会自动拉取新的 `catalog.json`，新图分钟级生效（jsDelivr `@latest` 缓存）。

### 三种变更的自动处理对照

| 操作 | 脚本行为 | git 变更 |
|---|---|---|
| 新增图片 | 生成缩略图 + 写入 catalog.json | `images/新增.jpg` + `thumbs/新增.jpg` + catalog.json 更新 |
| 替换图片（同文件名覆盖） | mtime 检测 → 重生成缩略图 + catalog 更新 | 三个文件内容更新 |
| 删除图片 | 清 thumbs/ 孤儿 + catalog 移除 + `git add` 包含删除 | 原图 + 缩略图 + catalog.json 更新 |

### 参数一览

| 参数 | 作用 | 默认值 |
|---|---|---|
| `-m / --message` | 自定义 commit message | 根据变更自动生成（如 `+5 new, ~2 replaced`） |
| `--force` | 强制重生成**所有**缩略图（替换时 mtime 没变才需要） | `false` |
| `--dry-run` | 只生成缩略图 + catalog，**不碰 git** | `false` |
| `--no-push` | commit 了但不 push（网络不通或稍后手动 push） | `false` |
| `--thumb-width` | 缩略图宽度 | `400` |

### 前置依赖

```bash
pip install Pillow
```

## 注意

- `catalog.json` 由脚本自动生成，**勿手工编辑**
- 生产新图请对照「素材规格规则」逐项自检：JPEG / 最长边 ≤1440px / ≤500KB / RGB / 命名
- 脚本只扫 `images/` **一级目录**，子文件夹不处理（批量添加前请先把文件移到根目录）
- jsDelivr 在部分网络（IPv6 优先环境）不可达——为已知环境限制，真机正常网络无碍
