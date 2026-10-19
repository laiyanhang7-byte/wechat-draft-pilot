# 提交说明

## 这个 PR 做了什么

<!-- 一句话说清，例如：修复 draft/update 后表格样式塌陷 -->

## 关联 issue

<!-- 例如 Closes #12；没有就写「无」 -->

## 改动类型

- [ ] Bug 修复
- [ ] 新功能
- [ ] 文档 / 示例
- [ ] 重构（不改变行为）
- [ ] 测试补充
- [ ] 其他

## 自检清单

- [ ] 本地跑过 `python tests/test_video_iframe.py` 与 `python tests/test_core.py`，均输出 `{"ok": true}`
- [ ] 改动了 `scripts/` 下的代码时，已跑 `python scripts/wx_publish.py --help` 确认 CLI 未破坏
- [ ] **没有提交任何真实凭证**（AppID / AppSecret / access_token / media_id），配置只走环境变量或 `config.json`（已被 .gitignore 忽略）
- [ ] 涉及公众号 API 行为的改动，已注明是**真连验证**还是**未验证**（未验证请在文档里明写）
- [ ] 涉及新踩的坑，已补进 `docs/pitfalls.md`

## 验证证据

<!-- 贴命令输出、draft-get --check 结果、前后对比截图等。不要只写「测试通过」 -->

```bash
# 例如
$ python tests/test_core.py | tail -1
{"ok": true, "total": 25, "failed": 0}
```

## 影响范围与风险

<!-- 会影响哪些命令/平台？Windows 与 Linux 都验过吗？有无兼容性破坏 -->
