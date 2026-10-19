# 示例

这里的东西**不需要公众号凭证、不联网**，用来在正式接入前先看清「排版产物长什么样」。

## 一条命令跑通

```bash
pip install -r requirements.txt
python examples/demo_offline.py
```

产物落在 `examples/out/`（已 gitignore，随时可删）：

| 文件 | 说明 |
|---|---|
| `cover.jpg` | 自动生成的封面，900×383，标题按标点智能折行 |
| `preview.html` | 模拟公众号正文的预览页，**用浏览器打开就能点两张 SVG 卡片** |
| `card_reveal.svg` | 点击展开卡（点一下，遮罩淡出、内容浮现） |
| `card_quiz.svg` | 答题卡（点一下看答案） |

自定义标题和输出目录：

```bash
python examples/demo_offline.py --title "你的标题" --digest "你的摘要" --out /tmp/demo
```

## 演示了什么 / 没演示什么

**演示了**：封面生成、SVG 交互卡结构、正文排版宽度与字号（677px / 17px / 行高 1.9）。

**没演示**：真正调公众号 API（上传素材、建草稿）。那一步必须有凭证，见
[docs/INSTALL.md](../docs/INSTALL.md)。演示页里的 HTML 结构与真实进草稿箱的正文一致，
所以在这里点得动的卡片，进草稿箱后同样点得动（微信正文会保留 SVG 的 `animate begin="click"`，
真连验证见 [docs/pitfalls.md](../docs/pitfalls.md)）。

## 关于字体

封面需要中文字体。脚本按 Windows 微软雅黑 → macOS 苹方 → Linux 文泉驿/Noto 的顺序自动探测；
都没找到时退回 PIL 内置字体（英文正常，中文可能显示方框）。要指定字体：

```bash
# 方式一：环境变量不行，用 config.json
{"font_path": "C:/Windows/Fonts/simhei.ttf", "brand_footer": "你的落款"}
```

或直接改 `scripts/wx_publish.py` 里的 `FONT_CANDIDATES`。
