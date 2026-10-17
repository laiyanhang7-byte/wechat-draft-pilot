---
name: wechat-draft-pilot
description: 微信公众号草稿箱全自动发布技能。覆盖完整流水线：AI 写稿（Markdown）→ md2wechat 主题排版 → AI 封面生成与裁切 → 品牌视频自动嵌入（wxv iframe 模板）→ SVG 交互卡（点击展开/答题卡）→ 直进草稿箱 → 服务器侧真连验证（乱码/表格/视频/图逐项核对）。触发词：发公众号、公众号文章、草稿箱、公众号排版、嵌视频、SVG 交互排版。所有 API 写法均经真连验证，踩坑全集在 docs/pitfalls.md（draft/update 乱码三坑、选择器特异性、视频四条路实验矩阵、wxv id 获取与复用）。
---

# wechat-draft-pilot — 微信公众号草稿箱全自动发布

凭证从环境变量 `WECHAT_APP_ID` / `WECHAT_APP_SECRET` 或本仓库 `config.json` 读取（参考 config.example.json），**不内嵌任何凭证**。

## 主入口

```bash
SK="<本仓库路径>/scripts/wx_publish.py"

python -X utf8 "$SK" status                 # 凭证体检 + 素材库统计（输出 {"ok": true,...}）
python -X utf8 "$SK" publish 文章.html --title "标题" --author "作者" --digest "摘要" --cover 封面.jpg
python -X utf8 "$SK" publish 文章.html --title "标题" --video wxv_XXX   # 自动嵌视频
python -X utf8 "$SK" draft-list 5           # 草稿箱最新 5 篇
python -X utf8 "$SK" draft-get <media_id> --check   # 拉草稿 + 乱码/视频/表格检验
python -X utf8 "$SK" update <media_id> 文章.html --title "标题"  # 全量更新（显式 UTF-8 防乱码）
python -X utf8 "$SK" video-add 视频.mp4 --title "标题"          # 上传视频到素材库
python -X utf8 "$SK" video-list             # 素材库视频列表
```

## 标准流水线（长文为例）

1. **写稿**：Markdown（结构：引言 > 多个 h2 章节 > 表格/引用/清单），存工作区。
2. **排版**：`md2wechat convert 文章.md 文章.html --theme 你的主题`
   （convert 必须显式传 --theme，.env 的 THEME 无效；主题规范见 docs/pitfalls.md 第三节）。
3. **封面**：ImageGen 生成 → PIL 裁 900x383（2.35:1）；或 `publish` 不传 --cover 时自动生成文字封面。
4. **视频（可选）**：`publish --video wxv_XXX`，播放器自动插到第一个 h2 之后。
5. **进草稿箱**：`publish` 或 `update <media_id>`（改已存在的稿）。
6. **真连验证（强制）**：`draft-get <media_id> --check`，核对 garble 全 0、表格/视频/图数量。
7. **发布**：人工在手机上点发布（微信规定必须人工；订阅号每天群发限 1 次）。

## 视频嵌入规则（重要）

- 微信正文视频唯一可靠格式是 **iframe + wxv_ 前缀 ID**（`video_iframe()` 模板已内置，13 项单测见 tests/）。
- 新视频入池：`video-add` 上传 → 后台编辑器随便找篇草稿手动插入该视频 → `draft-get` 拉 iframe 提取 `data-mpvid`（wxv_ 开头）→ 存档复用。API 直接拿到的 vid 是 apiv_ 前缀，前端不渲染。

## SVG 交互卡（可选花活）

`scripts/svg_cards.py`：`click_reveal_card()`（点击展开）、`quiz_card()`（答题卡）。
生成 HTML 片段拼进 content 即可，微信完整保留 animate click 动画。

## 排版主题定制

主题 = 普通 CSS：`<npm全局node_modules>/md2wechat/themes/markdown/<名字>.css`。
规范：`#nice` 前缀、纯静态值、禁 CSS 变量/calc/box-shadow。
**必须先 grep basic.css 拿真实选择器对位写**（`#nice table tr th`、`#nice .multiquote-1 p` 等深选择器），浅选择器必输。

## 铁律

- 发布前**必须** `draft-get --check` 真连验证，乱码指标全 0 才算完成。
- draft/update 的 JSON 必须 `ensure_ascii=False` 显式 UTF-8（详见 docs/pitfalls.md 第一节，曾致全文乱码事故）。
- 新视频/新主题/新写法，先小草稿实验再上正稿。
- **合规红线**：只做"自动进草稿箱 + 人工审核 + 人工点发布"，不接入 freepublish 全自动发布（2026-04 运营规范明令禁止接口自动化替代真人发布，见 docs/pitfalls.md 第七节）。
