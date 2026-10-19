# 贡献指南

参与本项目即表示你同意遵守[行为准则](CODE_OF_CONDUCT.md)。

## 提交踩坑案例（最有价值的贡献）

1. Fork → 新建分支 `pitfall/<主题>`
2. 在 `docs/pitfalls.md` 对应章节补充：**现象 → 根因 → 验证方法 → 正确写法**
3. 结论必须真连验证过，附上错误码/复现步骤
4. PR 描述里写清复现环境（认证状态、平台）

## 代码改动

- 保持"机读输出"约定：所有命令成功时最后输出 `{"ok": true, ...}`
- 新增功能先开 Issue 讨论
- 改动 `scripts/` 后本地至少跑这两条，都要 `"ok": true`：

  ```bash
  python -X utf8 tests/test_video_iframe.py
  python -X utf8 tests/test_core.py
  ```

- 新增可测的纯函数请补进 `tests/test_core.py`（不触网、不需要凭证）
- CI 全绿才能合并（三平台矩阵 + 密钥泄漏扫描）

## 开发环境

```bash
pip install -r requirements.txt
python -X utf8 scripts/wx_publish.py --help   # CLI 未破坏
```

## 安全红线

- 任何凭证（AppID/AppSecret/token/media_id）严禁入库，CI 会扫
- 不要提交自动发布相关功能（见 pitfalls 第七节运营规范红线）

