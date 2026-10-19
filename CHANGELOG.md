# 更新日志

本项目遵循[语义化版本](https://semver.org/lang/zh-CN/)。格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)。

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
