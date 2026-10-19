# -*- coding: utf-8 -*-
"""零配置演示：不联网、不需要公众号凭证，直接看排版产物长什么样。

跑这个脚本能看到三样东西（全部生成到 examples/out/）：
  1. cover.jpg        —— 自动封面（900x383，标题自动折行）
  2. preview.html     —— 模拟公众号正文的预览页（含两张可点击的 SVG 交互卡）
  3. card_*.svg       —— 两张 SVG 卡片的裸文件，可直接贴进任意 HTML

用法:
  python examples/demo_offline.py
  python examples/demo_offline.py --title "自定义标题" --out mydir

设计说明：这个脚本刻意只走本地能力（Pillow + 字符串模板），
用来验证「排版链路本身」没问题；真发草稿箱需要凭证，见 README。
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))

import wx_publish  # noqa: E402
import svg_cards  # noqa: E402


def build_article(title, digest, cover_rel, card_reveal, card_quiz, cover_ok=True):
    """拼一个接近公众号正文的 HTML：宽度、字号、行距按手机端阅读习惯"""
    if cover_ok:
        cover_block = '<img class="cover" src="%s" alt="自动生成的封面">' % cover_rel
    else:
        cover_block = ('<div class="tip">本机没找到可渲染中文的字体，封面已跳过。'
                       '指定字体见 examples/README.md「关于字体」。</div>')
    return """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
  body {{ margin:0; padding:0; background:#f7f7f7; font-family:-apple-system,BlinkMacSystemFont,"Helvetica Neue","PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif; }}
  .phone {{ max-width:677px; margin:0 auto; background:#fff; padding:20px 16px 60px; }}
  h1 {{ font-size:22px; line-height:1.4; color:#1a1a1a; margin:8px 0 6px; }}
  .meta {{ color:#999; font-size:14px; margin-bottom:18px; }}
  .cover {{ width:100%; border-radius:6px; display:block; margin:0 0 20px; }}
  p {{ font-size:17px; line-height:1.9; color:#3f3f3f; margin:0 0 18px; }}
  h2 {{ font-size:19px; color:#1a1a1a; margin:30px 0 14px; padding-left:10px; border-left:4px solid #1D9E75; }}
  .tip {{ background:#f2f8f6; border-radius:6px; padding:14px 16px; font-size:15px; color:#3d6b5d; line-height:1.8; }}
  .footer {{ margin-top:36px; padding-top:16px; border-top:1px solid #eee; color:#aaa; font-size:13px; text-align:center; }}
</style>
</head>
<body>
<div class="phone">
  <h1>{title}</h1>
  <div class="meta">{digest} · 零配置演示</div>
  {cover_block}
  <p>这一段是普通正文，用来对比手机端的字号与行距。真实发布时，这段 HTML 由
  <a href="https://www.npmjs.com/package/md2wechat">md2wechat</a> 从 Markdown 转出，
  本项目负责把它安全地送进草稿箱。</p>

  <h2>交互卡：点一下试试</h2>
  <p>下面这张卡片在微信正文里可以真实点击展开（双 g 层 + <code>animate begin="click"</code>，
  是实测能穿过微信过滤器的写法）。在这里点同样有效：</p>
  {card_reveal}

  <h2>答题卡：另一种交互形态</h2>
  {card_quiz}

  <div class="tip">
    <strong>为什么用 SVG 而不是 GIF？</strong><br>
    GIF 体积大、文字糊；SVG 卡片是矢量、可点击、能被微信正文保留，
    且无需外链资源（正文里外链会被剥）。
  </div>

  <div class="footer">本页面由 examples/demo_offline.py 生成 · 不联网、不需要凭证</div>
</div>
</body>
</html>
""".format(title=title, digest=digest, cover_block=cover_block,
           card_reveal=card_reveal, card_quiz=card_quiz)


def main():
    ap = argparse.ArgumentParser(description="零配置演示：生成封面 + SVG 卡片 + 预览页")
    ap.add_argument("--title", default="公众号排版，其实可以全自动", help="演示文章标题")
    ap.add_argument("--digest", default="从 Markdown 到草稿箱", help="摘要")
    ap.add_argument("--out", default=os.path.join(HERE, "out"), help="输出目录")
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    font = wx_publish.detect_font()
    wx_publish.FONT_PATH = font

    # 1) 自动封面（老版本 Pillow 缺中文字体时可能画不出中文，降级但不中断演示）
    cover_path = os.path.join(args.out, "cover.jpg")
    cover_ok = True
    try:
        wx_publish.make_cover(args.title, cover_path)
    except Exception as e:
        cover_ok = False
        print("跳过封面生成（%s: %s）" % (type(e).__name__, e))

    # 2) 两张 SVG 卡片
    reveal = svg_cards.click_reveal_card(
        640, 380, "#FF9500", "点我查看", "演示卡片", "轻点这块区域",
        "#1A3060", "排版自动化能省多少时间", ["以前：一篇 40 分钟", "现在：排版 0 分钟"], "点一下展开")
    quiz = svg_cards.quiz_card(
        640, 260, "微信正文里能执行 JavaScript 吗？",
        ["不能。所以复制类交互只能做到「长按复制」", "但 SVG 的点击动画可以保留"], footer="答案就在卡里")

    reveal_file = os.path.join(args.out, "card_reveal.svg")
    quiz_file = os.path.join(args.out, "card_quiz.svg")
    for path, content in ((reveal_file, reveal), (quiz_file, quiz)):
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

    # 3) 预览页
    preview = os.path.join(args.out, "preview.html")
    html = build_article(args.title, args.digest, "cover.jpg", reveal, quiz, cover_ok=cover_ok)
    with open(preview, "w", encoding="utf-8") as f:
        f.write(html)

    files = ["card_reveal.svg", "card_quiz.svg", "preview.html"]
    print("字体: %s" % (font or "未找到中文字体，已退回 PIL 内置字体（中文可能缺字）"))
    if cover_ok:
        files.insert(0, "cover.jpg")
        print("封面: %s (%d 字节)" % (cover_path, os.path.getsize(cover_path)))
    else:
        print("封面: 已跳过")
    print("卡片: %s / %s" % (reveal_file, quiz_file))
    print("预览: %s" % preview)
    print(json.dumps({"ok": True, "out": args.out, "files": files,
                      "font_found": bool(font), "cover": cover_ok}, ensure_ascii=False))


if __name__ == "__main__":
    main()
