# -*- coding: utf-8 -*-
"""SVG 交互卡生成器（公众号正文可点开的卡片）
用法:
  from svg_cards import click_reveal_card, quiz_card
  html = click_reveal_card(640, 380, "#FF9500", "点我查看", "副标题", "提示",
                           "#1A3060", "揭晓标题", ["行1", "行2"], "落款")
  html = quiz_card(640, 240, "问题？", ["答案1", "答案2"], footer="品牌落款")
原理: 双 g 层 + animate begin="click"，遮罩 opacity 1->0、内容 0->1，restart="never"。
微信正文保留此代码（真连验证）。注意文本引号用数字实体 &#8220; 等。
"""
import html as _html


def _esc(s):
    return _html.escape(s, quote=False)


def click_reveal_card(w, h, cover_bg, tip1, tip2, hint, reveal_bg, title, lines, footer=""):
    lines_svg = ""
    y = 150
    for ln in lines:
        lines_svg += '<text x="70" y="%d" fill="#FFD8A8" font-size="24">%s</text>' % (y, _esc(ln))
        y += 52
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" '
            'style="display:block;width:100%%;vertical-align:middle;margin:12px 0;">\n'
            '<g opacity="0">\n<rect x="0" y="0" width="%d" height="%d" rx="16" fill="%s"/>\n'
            '<text x="%d" y="80" text-anchor="middle" fill="#FFFFFF" font-size="34" font-weight="bold">%s</text>\n'
            '%s\n<text x="%d" y="%d" text-anchor="middle" fill="#9FE1CB" font-size="20">%s</text>\n'
            '<animate attributeName="opacity" begin="click" values="0;1" to="1" from="0" dur="0.4s" '
            'fill="freeze" restart="never" calcMode="spline" keyTimes="0;1" keySplines="0.4 0 0.2 1"/>\n</g>\n'
            '<g opacity="1">\n<rect x="0" y="0" width="%d" height="%d" rx="16" fill="%s"/>\n'
            '<text x="%d" y="%d" text-anchor="middle" fill="#FFFFFF" font-size="40" font-weight="bold">%s</text>\n'
            '<text x="%d" y="%d" text-anchor="middle" fill="#FFF5E0" font-size="26">%s</text>\n'
            '<text x="%d" y="%d" text-anchor="middle" fill="#FFE8C0" font-size="20">%s</text>\n'
            '<animate attributeName="opacity" begin="click" values="1;0" to="0" from="1" dur="0.4s" '
            'fill="freeze" restart="never" calcMode="spline" keyTimes="0;1" keySplines="0.4 0 0.2 1"/>\n</g>\n</svg>'
            ) % (w, h, w, h, _esc(reveal_bg), w // 2, _esc(title), lines_svg, w // 2, h - 40, _esc(footer),
                 w, h, _esc(cover_bg), w // 2, h // 2 - 40, _esc(tip1), w // 2, h // 2 + 15, _esc(tip2),
                 w // 2, h // 2 + 70, _esc(hint))


def quiz_card(w, h, question, answer_lines, footer=""):
    ans = ""
    y = 170
    for ln in answer_lines:
        ans += ('<text x="%d" y="%d" text-anchor="middle" fill="#FFFFFF" font-size="26">%s</text>'
                ) % (w // 2, y, _esc(ln))
        y += 46
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" '
            'style="display:block;width:100%%;vertical-align:middle;margin:12px 0;">\n'
            '<g opacity="0">\n<rect x="0" y="0" width="%d" height="%d" rx="16" fill="#0F6E56"/>\n'
            '%s\n<text x="%d" y="%d" text-anchor="middle" fill="#C0DD97" font-size="20">%s</text>\n'
            '<animate attributeName="opacity" begin="click" values="0;1" to="1" from="0" dur="0.4s" '
            'fill="freeze" restart="never" calcMode="spline" keyTimes="0;1" keySplines="0.4 0 0.2 1"/>\n</g>\n'
            '<g opacity="1">\n<rect x="0" y="0" width="%d" height="%d" rx="16" fill="#1D9E75"/>\n'
            '<text x="%d" y="%d" text-anchor="middle" fill="#FFFFFF" font-size="30" font-weight="bold">%s</text>\n'
            '<text x="%d" y="%d" text-anchor="middle" fill="#E1F5EE" font-size="22">点这里看答案</text>\n'
            '<animate attributeName="opacity" begin="click" values="1;0" to="0" from="1" dur="0.4s" '
            'fill="freeze" restart="never" calcMode="spline" keyTimes="0;1" keySplines="0.4 0 0.2 1"/>\n</g>\n</svg>'
            ) % (w, h, w, h, ans, w // 2, h - 40, _esc(footer), w, h, w // 2, h // 2 - 30, _esc(question),
                 w // 2, h // 2 + 30)


if __name__ == "__main__":
    demo = click_reveal_card(640, 380, "#FF9500", "点我查看", "演示卡片", "轻点这块区域",
                             "#1A3060", "标题", ["第一行", "第二行"], "落款")
    out = "svg_demo.html"
    with open(out, "w", encoding="utf-8") as f:
        f.write(demo)
    print('{"ok": true, "demo": "%s"}' % out)
