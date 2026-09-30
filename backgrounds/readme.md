# backgrounds/ — 主页主题背景源图目录

把要上架的主题背景**源图**（任意尺寸，建议竖屏）放本目录，脚本自动完成：

1. 压缩产物输出到 `backgrounds_opt/`（最长边 ≤1440px、文件 ≤500KB JPEG）
2. 写入 `catalog.json` 顶层 `backgrounds` 数组（App 在线更新主页背景用）
3. 随 git 一起推送

## 命名约定（与 App 内置背景对应）

| 文件名 | 主题 |
|---|---|
| `bg_theme_1.jpg` | 山湖/雪山 |
| `bg_theme_2.jpg` | 花海/花园 |
| `bg_theme_3.jpg` | 海滩/日落 |
| `bg_theme_4.jpg` | 城市天际线 |
| `bg_theme_N.jpg` | 新增主题依次编号 |

- 支持格式：jpg / jpeg / png / webp（产物统一转 .jpg）
- 增 / 删 / 改后直接运行 `py scripts\sync.py`，处理逻辑与主图库一致（mtime 检测替换、孤儿自动清理）
- 注意：删除或重排中间编号会影响 App 端按 id 引用，新增只往尾部追加

## 素材规范

- 内容：插画必须自带 Logo（"Puzzle Master" 或 "Jigsaw Master"，居中偏上），App 不再叠加文字
- 副标题等文案也可烘焙进图
- 尺寸：竖屏，源图任意尺寸（脚本自动缩放到 ≤1440px）
- 格式：JPEG（产物），源图可为 jpg/png/webp

## 完整推送流程

### 1. 放入/替换源图

把背景图放到本目录，文件名按上表约定。

### 2. 同步到 App 内置目录（可选，正式发布版需要）

把压缩产物复制到 App 的 drawable-nodpi 目录：

```powershell
Copy-Item "image-assets\backgrounds_opt\bg_theme_1.jpg" "app\src\main\res\drawable-nodpi\bg_theme_1.jpg" -Force
Copy-Item "image-assets\backgrounds_opt\bg_theme_2.jpg" "app\src\main\res\drawable-nodpi\bg_theme_2.jpg" -Force
Copy-Item "image-assets\backgrounds_opt\bg_theme_3.jpg" "app\src\main\res\drawable-nodpi\bg_theme_3.jpg" -Force
Copy-Item "image-assets\backgrounds_opt\bg_theme_4.jpg" "app\src\main\res\drawable-nodpi\bg_theme_4.jpg" -Force
```

### 3. 运行同步脚本

在仓库根目录下执行：

```powershell
py scripts\sync.py
```

脚本自动完成：压缩背景 → 重建 catalog.json → git add/commit/pull --rebase/push

常用参数：

```powershell
py scripts\sync.py --dry-run             # 只处理图片，不做 git 操作
py scripts\sync.py --force               # 强制重压缩所有背景
py scripts\sync.py -m "feat: 更新背景4"  # 自定义 commit message
py scripts\sync.py --no-push             # 处理 + commit，但不推送
```

### 4. 验证 CDN

推送后等几分钟，访问以下 URL 确认 backgrounds 数组已更新：

```
https://cdn.jsdelivr.net/gh/Besta-NZ/image-assets@latest/catalog.json
```

## 目录结构

```
image-assets/
├── backgrounds/          ← 源图（你放图的地方，任意尺寸）
├── backgrounds_opt/       ← 脚本自动生成（≤1440px & ≤500KB），勿手动改
├── catalog.json           ← 脚本自动生成，含 backgrounds 数组
├── images/                ← 主图库原图
├── thumbs/                ← 主图库缩略图
└── scripts/
    └── sync.py
```
