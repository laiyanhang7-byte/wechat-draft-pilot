# 文章排版模板

十套完整文章排版模板，分两个族：

- **内联族（7 套）**：样式直接写在元素 `style` 上，**可直接进草稿箱**（只需把外链图换成素材库地址）
- **网页级（3 套）**：带 `<style>` 块 / CSS 变量 / `@media` / 外链字体，公众号会剥掉样式，需内联或改写成主题

字体、配色、插画全部抽取成机器可读规格（`theme.json`）并带指纹，改动可被自动校验抓出来。

## 内联族（可直接发公众号）

| slug | 名称 | 配色 | 插画 | 适用 |
|---|---|---|---|---|
| `chuli-fenfa` | 踔厉奋发启新程 | 8 色（红金商务） | 11 张 / 出现 21 次 | 年度总结、动员大会、开门红 |
| `light-minimal` | 轻简设计 | 7 色（留白克制） | 8 张 / 出现 15 次 | 品牌简述、产品介绍、简约长文 |
| `rigorous-summary` | 严谨务实总结提升 | 8 色（蓝灰稳重） | 14 张 / 出现 23 次 | 部门总结、述职报告、工作复盘 |
| `cohesion-2024` | 凝心聚力2024蓄力前行 | 8 色（红蓝撞色） | 14 张 / 出现 21 次 | 年会、团队动员、年度规划 |
| `review-new-ideas` | 回顾总结启新思 | 8 色（暖橙复古） | 10 张 / 出现 12 次 | 季度回顾、项目复盘、经验沉淀 |
| `visual-minimal` | 视觉极简 | 6 色（黑白极简） | 6 张 / 出现 15 次 | 观点输出、深度评论、极简审美 |
| `year-end-summary` | 年底工作总结 | 8 色（稳重商务） | 5 张 / 出现 11 次 | 年终总结、绩效汇报、成果展示 |

> 内联族模板**未指定 font-family**，使用公众号默认字体（不是漏了，`theme.json` 的 `font_note` 已注明）。

## 网页级（设计参考）

| slug | 名称 | 配色 | 字体 | 插画 | 适用 |
|---|---|---|---|---|---|
| `cream-magazine` | 奶油杂志风 | 7 色（纸白 `#FDFBF7` / 焦糖 `#B4815F` / 深棕 `#6B4F3A` / 奶油 `#F3E9DA`） | 思源宋体 900 + 思源黑体 | 3 张 / 出现 4 次 | 深度长文、品牌内容、生活方式 |
| `dopamine-pop` | 多巴胺撞色风 | 7 色（亮黄 `#FFD93D` / 橙 `#FF9F45` / 粉 `#FF6B9D` / 蓝 `#4D96FF` / 青柠 `#7ED957`） | 站酷快乐体 + 思源黑体 | 4 张 / 出现 12 次 | 轻松话题、活动种草 |
| `forest-natural` | 森系自然风 | 8 色（米白 `#FBF7EE` / 叶绿 `#7A9B63` / 苔藓 `#556B46` / 深苔 `#3E5232`） | 马善政毛笔 + 思源宋体 + 思源黑体 | 4 张 / 出现 12 次 + 2 个手绘枝丫 SVG | 治愈、自然、慢生活 |

## 目录结构

```
templates/
├── extract.py                 抽取 / 校验 / 下载素材（唯一维护入口）
├── registry.json              三套模板索引（自动生成）
├── cream-magazine/
│   ├── template.html          原始模板（逐字节保留，唯一真源）
│   ├── theme.json             抽取出的规格（自动生成，勿手改）
│   └── assets/
│       ├── manifest.json      插画清单：URL / 文件 / 指纹 / 尺寸
│       └── *.jpg              插画素材（已下载，最长边 1400）
├── dopamine-pop/              同上
└── forest-natural/            同上
```

## 发成草稿箱（验收用）

内联族可以直接发。脚本会：取 `<body>` → 删 `<script>` → 把外链插画逐张上传正文图床 →
替换 `src`/`data-src` → 建草稿 → 自动验收 → 桌面生成预览。

```bash
# 先干跑，不联网：看会替换多少处、有没有漏图
python -X utf8 templates/publish_template.py --slug chuli-fenfa --dry-run

# 真发单套
python -X utf8 templates/publish_template.py --slug chuli-fenfa

# 7 套内联族全发
python -X utf8 templates/publish_template.py --all
```

- 上传结果缓存在 `assets/uploaded.json`（已 gitignore），重跑不重复上传。
- 网页级 3 套默认拒绝（会发成白文），要发需显式加 `--allow-css-var`。
- 每次发布都会输出 `media_id` + 验收明细（乱码三指标 / h2 数 / 配图数 / 标题）。

## 常用命令

```bash
# 抽取（模板改动后重跑，刷新 theme.json 与 registry.json）
python -X utf8 templates/extract.py

# 校验（CI 用；模板被改坏 / 插画丢了 / 颜色对不上都会 FAIL）
python -X utf8 templates/extract.py --verify
python -X utf8 tests/test_templates.py

# 重新下载插画（原图来自外链，已落盘；外链失效时这里是唯一来源）
python -X utf8 templates/extract.py --fetch-assets

# 看公众号兼容性（哪些写法会被草稿箱剥掉）
python -X utf8 templates/extract.py --wechat-report
```

## ⚠️ 网页级 3 套：不能直接发公众号

奶油 / 多巴胺 / 森系这三套是完整网页（`<style>` + CSS 变量 + `@media` + 外链字体 + 外链插画 + 交互脚本）。
**公众号正文会把这些全部剥掉**，直接 `publish` 会得到一篇没有样式的白文。

`--wechat-report` 会列出每个模板的 6 类问题：

| 问题 | 公众号行为 | 处理方式 |
|---|---|---|
| `<style>` 块 | 整块剥离 | 样式必须内联到元素的 `style` 属性 |
| 外链样式表 | 不加载 | 改用系统字体栈（宋体/黑体/苹方） |
| `var(--x)` CSS 变量 | 不支持 | 展开为具体色值/字体名 |
| `@media` | 不生效 | 宽度由客户端决定，删掉响应式 |
| 外链图片 | 剥掉 | 先上传素材库换成 `mmbiz.qpic.cn` 地址 |
| `<script>` | 禁止 | 删掉模板说明面板 |

所以正确用法是二选一：

1. **作为设计参考**：在浏览器里打开 `template.html` 看版式、配色、字号层级，
   然后把结构类（`.kicker` / `h1.title` / `.quote` / `.magframe` 等）套到自己的 HTML 上，
   用 `md2wechat` 主题或内联样式实现同样效果；
2. **改写成 md2wechat 主题**：把 `theme.json` 里的 `palette` / `fonts` / `type_scale`
   映射成 `#nice` 前缀的 CSS（规范见 `docs/pitfalls.md` 第三节）。

`theme.json` 就是为这两条路准备的结构化规格——颜色、字体、字号、结构类、插画位置全在里面，
不用再翻 HTML 找。

## 插画素材说明

- 全部 **79 张唯一图**（内联族 68 + 网页级 11，合计出现 146 次）已下载到各自 `assets/`，
  **不依赖外链**（xmyeditor / doubaocdn 的链接都会失效）。
- **按原格式保存，不无脑转 JPEG**：
  - GIF 原样保留（重新编码会把动图变静图）
  - PNG 保留 alpha 通道（转 JPEG 会把透明背景变成白块）
  - 只有 JPEG 才做等比缩放（最长边 1400、q88）
- `manifest.json` 记录每张图的原始 URL、文件名、sha256、字节数、实际尺寸，
  可用 `tests/test_templates.py` 验证「素材没被替换、没被删」。
- 森系另有 2 个内联 `<svg class="twig">` 手绘枝丫（矢量，不是图片），改模板时别删。

## 校验了什么（190 + 380 项）

`extract.py --verify`（190 项）与 `tests/test_templates.py`（380 项）合计覆盖：

1. `template.html` 的 sha256 与 `theme.json` 记录一致（模板未被偷偷改动）
2. 配色变量与登记值完全一致，且每个色值都真实出现在 HTML 中
3. 字体栈与登记值完全一致（内联族未指定字体时，必须写明 `font_note`）
4. 插画清单双向对齐（HTML ↔ theme.json），唯一数（79）与出现次数（146）都对
5. 内联 SVG 数量一致（森系 twig × 2 不能丢）
6. 网页级模板：说明面板里声明的每个色值，都存在于 CSS 变量表中（这就是「颜色要一致」）
7. 网页级模板：结构类（`.kicker` / `h1.title` …）在 HTML 中确实被使用
8. 插画文件真实存在于磁盘、指纹一致、非空
9. 十套模板配色互不相同（防复制粘贴串味）
10. 内联族确认没有 `<style>` / `var()` / `@media` 残留（否则不能直接发公众号）

已实测：改一个色值 / 删一张插画，校验都会 FAIL 并指出具体是哪项。
