# wechat-draft-pilot

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)
[![CI](https://github.com/laiyanhang7-byte/wechat-draft-pilot/actions/workflows/ci.yml/badge.svg)](../../actions)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux-lightgrey.svg)]()

**一句话：微信公众号"排版 → 草稿箱"全自动流水线 —— Markdown 进，排版好的文章直接躺在公众号草稿箱里，发布仍由人工一键确认。**

## 这解决什么问题

公众号后台编辑器排版慢、格式不可控、视频/配图坑多。本项目把整条链路脚本化：

```
Markdown 写稿 ──► md2wechat 主题排版 ──► 自动封面 ──► 视频/SVG 交互卡注入 ──► 草稿箱 API
                                                                      │
                                                    人工审核 + 手机一键发布 ◄┘
```

所有 API 写法均经**真实公众号真连验证**，踩坑全集见 [docs/pitfalls.md](docs/pitfalls.md)（draft/update 乱码三连、正文嵌视频四条死路一条活路、配图裂图事故复盘、未认证订阅号权限矩阵）。

## 逐个击破的痛点（公众号富文本老大难）

| 痛点 | 症状 | 本项目方案 |
|---|---|---|
| **富文本乱码** | draft/update 后全文变 `\uXXXX` 转义或 `Ã©` 双编码，一次事故 1969 处 | 显式 UTF-8 双端写法已固化进代码；`--check` 输出乱码三指标，全 0 才放行 |
| **表格样式丢失** | 后台编辑器/第三方工具生成的表格在手机端样式塌陷 | 主题 CSS 深选择器对位规范（`#nice table tr th` 等）+ 排版链路一次性带上 |
| **SVG 被清洗** | 交互卡片、动画在正文里被微信过滤器剥掉 | 实测通过的 SVG 写法（双 g 层 + `animate begin="click"` + 实体引号），封装成两个生成器函数 |
| **视频嵌入死路** | mpvideo/video 标签/视频号组件全是空白或被清洗，四条路三条死 | 实验矩阵收官：wxv_ 播放器 iframe 是唯一全自动活路，`--video` 一条命令注入 |
| **正文配图裂图** | 素材接口的 url 嵌正文后手机端全部裂图 | 通道分离（uploadimg vs add_material）+ aHash 感知哈希配对自动修复 |
| **API 假乱码误判** | 拉回来的草稿"看着乱码"，其实是显示端问题 | 识别 content-type 无 charset 导致的 ISO-8859-1 误读，显式解码复验 |
| **权限盲区** | 不知道哪些接口自己的号能不能调 | 未认证订阅号权限矩阵实测（✅/❌48001/❌404 三档全列出） |
| **自动化封号风险** | 2026-04 新规禁止接口自动发布 | 刻意设计为"只进草稿箱 + 人工发布"，红线写进文档 |

## 功能一览

- **草稿箱全套**：publish（新建）/ update（全量更新）/ draft-list / draft-get（附乱码与结构自检）
- **自动封面**：不传封面时按标题自动生成 900x383 文字封面（字体可配）
- **视频嵌入**：`--video wxv_XXX` 自动把微信原生播放器 iframe 插到第一个 h2 后（含 wxv id 获取方法论）
- **SVG 交互卡**：点击展开卡、答题卡，微信正文完整保留动画
- **配图修复**：aHash 感知哈希配对，一键修复素材接口重压缩导致的正文裂图
- **真连验证**：`--check` 输出乱码三指标（`\u` 残留 / `Ã` 双编码 / U+FFFD），全 0 才算合格
- **机读输出**：所有命令成功时输出 `{"ok": true, ...}`，可无缝接入自动化流水线

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置凭证（二选一）
export WECHAT_APP_ID=你的AppID
export WECHAT_APP_SECRET=你的AppSecret
#   或复制 config.example.json 为 config.json 填入凭证

# 3. 冒烟：验证凭证 + 素材库统计
python scripts/wx_publish.py status

# 4. 排版好的 HTML 进草稿箱
python scripts/wx_publish.py publish article.html --title "标题" --digest "摘要"

# 5. 真连验证（强烈建议）
python scripts/wx_publish.py draft-get <media_id> --check
```

> **排版环节**：搭配 [md2wechat](https://www.npmjs.com/package/md2wechat)（npm 全局安装）将 Markdown 转成微信兼容 HTML，支持自定义主题（`#nice` 前缀 CSS，规范见 pitfalls 第三节）。不装 md2wechat 也可直接使用任意来源的 HTML。

## 配置

`config.example.json` → 复制为 `config.json`（已被 .gitignore 忽略）：

```json
{
  "app_id": "你的AppID",
  "app_secret": "你的AppSecret",
  "author": "默认作者名",
  "brand_footer": "自动封面页脚落款",
  "font_path": "C:\\Windows\\Fonts\\msyhbd.ttc"
}
```

环境变量 `WECHAT_APP_ID` / `WECHAT_APP_SECRET` 优先级高于 config.json。**凭证严禁写进代码或提交进仓库。**

## 目录结构

```
├── scripts/
│   ├── wx_publish.py          # 主入口：publish/update/draft-*/video-*
│   ├── svg_cards.py           # SVG 点击展开卡 / 答题卡生成器
│   └── fix_content_images.py  # aHash 配对修复正文裂图
├── docs/
│   └── pitfalls.md            # 踩坑全集（本仓库最有价值的部分之一）
├── config.example.json
└── .github/workflows/ci.yml   # CI：语法检查 + 冒烟 + 密钥泄漏扫描
```

## 已知限制（诚实声明）

- 未认证个人订阅号的 API 边界实测：数据统计/标签/粉丝/渠道码等接口 48001 硬墙，详见 pitfalls 第六节
- 正式发布必须人工在手机端点击（微信规定）；**本项目刻意不接入全自动发布**——2026-04 运营规范明令禁止接口自动化替代真人发布，详见 pitfalls 第七节
- 视频嵌正文仅支持已入池的 wxv_ id（获取方法见 pitfalls 第二节）

## 适用与免责

适用于有公众号内容发布需求的个人与团队自用。使用本项目请遵守《微信公众平台运营规范》：本项目只负责"进草稿箱"，内容的合规性与发布决策由使用者负责。

## 贡献

踩到新坑？欢迎 PR 补充 [docs/pitfalls.md](docs/pitfalls.md)——这份文档靠真实案例持续生长。流程见 [CONTRIBUTING.md](CONTRIBUTING.md)。

## License

[MIT](LICENSE)
