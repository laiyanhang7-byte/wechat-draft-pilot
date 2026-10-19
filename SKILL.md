---
name: wechat-draft-pilot
description: 微信公众号草稿箱全自动发布技能。覆盖完整流水线：AI 写稿（Markdown）→ md2wechat 主题排版 → AI 封面生成与裁切 → 品牌视频自动嵌入（wxv iframe 模板）→ SVG 交互卡（点击展开/答题卡）→ 桌面预览 HTML（先看排版效果）→ 直进草稿箱 → 服务器侧自动验收（乱码/章节/配图/视频/标题逐项核对，不过即判失败）。两条硬性要求内置在代码里：发布前必出桌面预览、发布后必自动验收。触发词：发公众号、公众号文章、草稿箱、公众号排版、嵌视频、SVG 交互排版、排版预览。所有 API 写法均经真连验证，踩坑全集在 docs/pitfalls.md（draft/update 乱码三坑、选择器特异性、视频四条路实验矩阵、wxv id 获取与复用）。
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
python -X utf8 "$SK" draft-get <media_id> --check   # 手动拉草稿检验（publish 已自动做）
python -X utf8 "$SK" update <media_id> 文章.html --title "标题"  # 全量更新（显式 UTF-8 防乱码）
python -X utf8 "$SK" video-add 视频.mp4 --title "标题"          # 上传视频到素材库
python -X utf8 "$SK" video-list             # 素材库视频列表
```

## 两条硬性要求（写在代码里，不靠人记）

### 硬性要求 1：发布前必须生成桌面预览 HTML，让用户先看排版效果

`publish` / `update` **默认**会把即将发送的正文写成
`桌面/公众号预览_<标题>_<时间戳>.html`（自动补 UTF-8 声明、清理非法字符），
并在结果 JSON 的 `preview` 字段返回路径。

- **必须把 preview 路径明确告诉用户**，让用户先打开看排版效果，再决定是否发布。
- 禁止用 `--no-preview` 绕过；除非用户明确说"不用给我看"。
- 无桌面环境（服务器 / CI）用 `--preview-dir <目录>` 指定输出位置，**不允许静默跳过**；
  真找不到目录时工具会往 stderr 打 `[warn]`，此时必须在报告里说明"预览未生成"。

### 硬性要求 2：发布后必须自动验收，验收不过不得发布

`publish` / `update` 建完草稿后**自动** `draft/get` 拉回服务器侧内容，逐项核对：

| 验收项 | 判定 |
|---|---|
| 乱码三指标 | `\u` 残留 / `Ã` 双编码 / U+FFFD 全部为 0 |
| 正文非空 | 拉回内容非空白 |
| h2 章节数 | 与发出时一致 |
| 正文配图数 | 与发出时一致（发出时含 `mmbiz.qpic.cn` 才算） |
| 视频（传了 `--video` 时） | `<iframe` ≥ 1 且无 `<mpvideo>` 死路标签 |
| 标题 | 与发出时一致 |

- 任一项不过 → 输出 `{"ok": false, "error": "验收未通过：草稿已创建，请勿发布..."}` + 退出码 1，
  `failed` 字段列出具体哪几项。**草稿已经建出来了，但绝不能发布**，先按 detail 排查。
- 禁止用 `--no-verify` 跳过；只有排障时才允许，且必须在报告里说明"本次未验收"。
- 不要再用"再手动跑一次 draft-get --check"来替代自动验收——那是重复劳动，且容易忘。

## 标准流水线（长文为例）

1. **写稿**：Markdown（结构：引言 > 多个 h2 章节 > 表格/引用/清单），存工作区。
2. **排版**：`md2wechat convert 文章.md 文章.html --theme 你的主题`
   （convert 必须显式传 --theme，.env 的 THEME 无效；主题规范见 docs/pitfalls.md 第三节）。
3. **封面**：ImageGen 生成 → PIL 裁 900x383（2.35:1）；或 `publish` 不传 --cover 时自动生成文字封面。
4. **视频（可选）**：`publish --video wxv_XXX`，播放器自动插到第一个 h2 之后。
5. **进草稿箱 + 预览 + 验收（一步完成）**：`publish` 或 `update <media_id>`
   —— 自动生成桌面预览 HTML、自动拉回服务器侧内容验收。
6. **把 preview 路径给用户看排版**，验收通过后才让用户去手机上点发布。
7. **发布**：人工在手机上点发布（微信规定必须人工；订阅号每天群发限 1 次）。

> 想先干跑不碰接口：`publish ... --dry-run` —— 只做本地校验并打印摘要（含视频插入位置、预览路径），
> 不建草稿、不消耗任何接口调用。

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

1. **发布前必须生成桌面预览 HTML，并把路径交给用户看排版**——默认行为，不许跳过。
2. **发布后必须自动验收通过才算完成**——`publish`/`update` 已内置，`ok:false` 的草稿绝不能发布。
3. draft/update 的 JSON 必须 `ensure_ascii=False` 显式 UTF-8（详见 docs/pitfalls.md 第一节，曾致全文乱码事故）。
4. 新视频/新主题/新写法，先小草稿实验再上正稿。
5. **合规红线**：只做"自动进草稿箱 + 人工审核 + 人工点发布"，不接入 freepublish 全自动发布（2026-04 运营规范明令禁止接口自动化替代真人发布，见 docs/pitfalls.md 第七节）。

## 报告纪律

交付给用户时必须包含三样，缺一视为没做完：

1. **预览路径**（`preview` 字段）——让用户能自己打开看排版；
2. **验收结论**（`verified: true` + `verify_checks` 项数，或失败时 `failed` 明细）；
3. **media_id**——用户后续要 update 或手动发布都靠它。
