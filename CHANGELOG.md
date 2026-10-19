# 更新日志

本项目遵循[语义化版本](https://semver.org/lang/zh-CN/)。格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)。

## [未发布]

### 新增

- **零配置演示** `examples/demo_offline.py`：不联网、不需要凭证，一条命令生成封面 + 两张 SVG 交互卡 + 可点击的预览页
- `examples/sample-article.md`：示例稿件，覆盖表格/代码/列表三类易翻车组件
- `--dry-run`：`publish` / `update` 支持只做本地校验并打印将发送的内容摘要（含视频插入位置），不消耗接口调用
- `update` 补齐 `--video` 系列参数（之前只有 `publish` 能嵌视频，更新草稿时无法重新注入）
- `--help` 补全每个参数的中文说明
- CI 增加「离线演示」步骤，保证示例不腐坏

### 修复（自查发现，均为「静默错误」类问题）

- **假成功：接口报错被当成成功**。`status` / `draft-list` / `draft-get` / `video-list` 都不检查 `errcode`，
  而微信失败响应通常不带业务字段，于是 `.get("item", [])` 取到空值后仍输出 `{"ok": true}`。
  最典型的是 `status`——它是文档里写的「验证凭证」命令，**凭证错了它也报 ok**。
  新增 `api_check()` 统一判错，`errcode≠0` 一律输出 `ok:false` + 退出码 1。
- **文件不存在 / 编码不对直接抛 Python traceback**。新增 `read_html()`：友好报错 + 编码自动兜底
  （UTF-8-BOM → UTF-8 → GB18030），并拦下空文件与误传目录。国内用户从 WPS/Word 导出的 GBK HTML 以前直接崩。
- **空标题 / 超 64 字标题会被送到服务端才失败**，白跑一次封面上传。改为本地先校验。
- **自动封面写到 `scripts/` 源码目录**，污染仓库。改写到系统临时目录。
- **上传素材未关闭文件句柄**，Windows 下会锁文件。改用 `with`。
- **`video-add` 输出两行 JSON**，破坏「最后一行是机读结果」的约定。合并为一行。
- **封面标题折行**：原来按固定 12 字硬切，会把词拆成两半（「公众号排版，其实可以全自 / 动」）。改为优先在标点后断开、无标点按中点断、单行超长加省略号（`split_title`）。
- **封面在无中文字体机器上崩溃**：`make_cover` 原先直接 `ImageFont.truetype(FONT_PATH)`，字体为空时抛异常。新增 `detect_font()` / `_load_font()` / `_text_width()` 三级兜底。
- 单测 25 → 58 项，覆盖上述全部修复

## [1.0.0] - 2026-10-19

首个正式发布版。所有 API 行为均经**真实公众号真连验证**（未认证订阅号为主），踩坑结论沉淀在 [docs/pitfalls.md](docs/pitfalls.md)。

### 新增

- **草稿箱全套**：`publish`（新建）/ `update`（全量更新）/ `draft-list` / `draft-get`（附乱码与结构自检 `--check`）
- **自动封面**：不传封面时按标题生成 900×383 文字封面，字体可配
- **视频嵌入**：`--video wxv_XXX` 把微信原生播放器 iframe 插到第一个 `h2` 之后，附 wxv id 获取方法论
- **SVG 交互卡**：`click_reveal_card` / `quiz_card` 两个生成器，微信正文完整保留点击动画
- **配图修复**：`fix_content_images.py`，uploadimg 与 add_material 通道分离 + aHash 感知哈希自动配对
- **智能体接入**：Claude Code / Codex / WorkBuddy 的技能安装说明（`SKILL.md` + 文档）
- **测试**：`tests/test_video_iframe.py`（13 项）、`tests/test_core.py`（25 项，覆盖乱码三指标、SVG 结构、感知哈希）

### 关键设计决定

- **只进草稿箱，不自动群发**。2026-04 新规禁止接口自动发布，本项目刻意保留人工一键确认，红线写进文档。
- **凭证只走环境变量或 `config.json`**（`.gitignore` 已忽略），CI 内置密钥泄漏扫描兜底。

### 已知限制

- 未认证订阅号部分接口不可用（`48001` / `404`），权限矩阵见 `docs/pitfalls.md`
- 正文内不能执行 JS，复制类交互只能做到「长按复制」
- 仅验证 Windows 与 Linux；macOS 未做真连验证（CI 仅做语法与单测）

---

## 版本对照

| 版本 | 主要变化 |
|---|---|
| 1.0.0 | 首个正式版，草稿箱/封面/视频/SVG/配图修复全链路 |
