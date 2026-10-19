# 文章排版模板

三套完整文章排版模板，从原始 HTML 抽取成机器可读的规格（`theme.json`），
字体、配色、插画全部落盘并带指纹，改动可被自动校验抓出来。

| 模板 | 风格 | 配色 | 字体 | 插画 |
|---|---|---|---|---|
| `cream-magazine` | 奶油杂志风 · 大标题杂志排版，适合深度长文 / 品牌内容 / 生活方式 | 纸白 `#FDFBF7` · 焦糖 `#B4815F` · 深棕 `#6B4F3A` · 奶油 `#F3E9DA` · 正文 `#2E2A26` · 细线 `#E7DCC9` | 思源宋体（Serif 900）+ 思源黑体 | 3 张（出现 4 次） |
| `dopamine-pop` | 多巴胺撞色风 · 高饱和撞色 + 贴纸元素，适合轻松话题 / 活动种草 | 亮黄 `#FFD93D` · 橙 `#FF9F45` · 粉 `#FF6B9D` · 蓝 `#4D96FF` · 青柠 `#7ED957` · 墨 `#1F2430` · 米白 `#FFF9EF` | 站酷快乐体 + 思源黑体 | 4 张（出现 12 次） |
| `forest-natural` | 森系自然风 · 低饱和草木色 + 手绘枝丫，适合治愈 / 自然 / 慢生活 | 米白 `#FBF7EE` · 叶绿 `#7A9B63` · 苔藓 `#556B46` · 深苔 `#3E5232` · 墨绿 `#3D4A36` · 奶油 `#EFE7D6` · 细线 `#E2DAC6` | 马善政毛笔 + 思源宋体 + 思源黑体 | 4 张（出现 12 次）+ 2 个内联枝丫 SVG |

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

## ⚠️ 重要：这是「网页级模板」，不能直接发公众号

三套模板都是完整网页（`<style>` + CSS 变量 + `@media` + 外链字体 + 外链插画 + 交互脚本）。
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

- 全部 11 张（奶油 3 / 多巴胺 4 / 森系 4）已下载到各自的 `assets/`，**不依赖外链**（原外链会失效）。
- 统一缩到最长边 1400px、JPEG q88：公众号正文显示宽度 ≤720px，2 倍图足够，体积从 ~13MB 压到 ~2.3MB。
- `manifest.json` 记录每张图的原始 URL、文件名、sha256、字节数、实际尺寸，
  可用 `tests/test_templates.py` 验证「素材没被替换、没被删」。
- 森系另有 2 个内联 `<svg class="twig">` 手绘枝丫（矢量，不是图片），改模板时别删。

## 校验了什么（85 + 80 项）

`extract.py --verify`（85 项）与 `tests/test_templates.py`（80 项）合计覆盖：

1. `template.html` 的 sha256 与 `theme.json` 记录一致（模板未被偷偷改动）
2. `:root` 里每个色值都真实出现在 HTML 中
3. 字体栈与 `:root` 完全一致
4. 插画清单双向对齐（HTML ↔ theme.json），唯一数与出现次数都对
5. 内联 SVG 数量一致（森系 twig × 2 不能丢）
6. 模板自带说明面板里声明的每个色值，都存在于 CSS 变量表中（这就是「颜色要一致」）
7. 结构类（`.kicker` / `h1.title` …）在 HTML 中确实被使用
8. 插画文件真实存在于磁盘、指纹一致、非空
9. 三套模板配色互不相同（防复制粘贴串味）

已实测：改一个色值 / 删一张插画，校验都会 FAIL 并指出具体是哪项。
