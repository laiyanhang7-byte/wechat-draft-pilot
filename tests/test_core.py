# -*- coding: utf-8 -*-
"""核心纯函数本地验证：乱码自检 / SVG 卡片结构 / 感知哈希配对
不触网、不需要凭证。运行: python tests/test_core.py  → 最后输出 {"ok": true, ...}
覆盖 docs/pitfalls.md 里真连验证过的结论，防止重构时静默退化。"""
import os, sys, json

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
from wx_publish import garble_check, video_iframe  # noqa: E402
import wx_publish  # noqa: E402
import svg_cards  # noqa: E402

checks = []


def check(name, cond, detail=""):
    checks.append({"name": name, "pass": bool(cond), "detail": detail})


# ---------- 1. 乱码自检三指标 ----------
normal = "<p>正常的公众号正文，中文、English、emoji 🎉 都不该报警。</p>"
g = garble_check(normal)
check("正常正文三指标全 0", g == {"u_escape": 0, "double_encode": 0, "replacement_char": 0}, str(g))

escaped = "<p>" + "\\u4e2d\\u6587" + "</p>"          # 字面量 \uXXXX（未解码就被写进正文）
check("识别 \\uXXXX 转义", garble_check(escaped)["u_escape"] == 2, str(garble_check(escaped)))

double = "<p>Ã©Ã¨Ã </p>"                              # UTF-8 被当 Latin-1 二次编码
check("识别二次编码 Ã", garble_check(double)["double_encode"] == 3, str(garble_check(double)))

check("识别替换符 U+FFFD", garble_check("坏字\ufffd")["replacement_char"] == 1)

mixed = "<p>\\u4e2d Ã© \ufffd</p>"
gm = garble_check(mixed)
check("三指标同时命中互不干扰",
      gm == {"u_escape": 1, "double_encode": 1, "replacement_char": 1}, str(gm))

# ---------- 2. SVG 卡片：微信正文能保留的结构要素 ----------
card = svg_cards.click_reveal_card(640, 380, "#FF9500", "点我查看", "副标题", "提示",
                                   "#1A3060", "揭晓标题", ["行1", "行2"], "落款")
check("SVG 根节点与 viewBox", card.startswith("<svg xmlns=") and 'viewBox="0 0 640 380"' in card)
check("双 g 层（遮罩 + 内容）", card.count("<g opacity=") == 2)
check("两处 click 触发动画", card.count('begin="click"') == 2)
check("restart=never 防重播", card.count('restart="never"') == 2)
check("标签闭合", card.count("</svg>") == 1 and card.count("</g>") == 2)
check("宽度自适应 + 上下留白（微信兼容写法）", "width:100%" in card and "margin:12px 0" in card)

quiz = svg_cards.quiz_card(640, 240, "问题？", ["答案1", "答案2"], footer="落款")
check("答题卡同结构", quiz.count("<g opacity=") == 2 and quiz.count('begin="click"') == 2)
check("答题卡答案行数透传", "答案1" in quiz and "答案2" in quiz)
check("答题卡点击提示语", "点这里看答案" in quiz)

# ---------- 3. 文本转义：用户内容不得注入 SVG 标签 ----------
check("_esc 转义尖括号与 &",
      svg_cards._esc("a<b>&c") == "a&lt;b&gt;&amp;c", svg_cards._esc("a<b>&c"))
check("_esc 保留引号（quote=False，正文用实体引号）", svg_cards._esc('"x"') == '"x"')

evil = svg_cards.click_reveal_card(640, 380, "#FF9500", "<script>alert(1)</script>", "t", "h",
                                   "#1A3060", "<img onerror=x>", ["<b>"], "")
check("恶意标签被转义不落成真标签",
      "<script>" not in evil and "<img " not in evil and "&lt;script&gt;" in evil)

# ---------- 4. 感知哈希：配图配对 ----------
try:
    from PIL import Image
    from fix_content_images import ahash, dist

    def solid(color, size=(64, 64)):
        return Image.new("RGB", size, color)

    a = ahash(solid((10, 10, 10)))
    check("ahash 输出 16x16=256 位且只含 0/1",
          len(a) == 256 and set(a) <= {"0", "1"}, f"len={len(a)}")
    check("纯色图全 0（无高于均值像素）", a == "0" * 256, a[:16] + "...")

    # 左黑右白：与纯黑差异明显，与自身差异为 0
    half = Image.new("RGB", (64, 64), (0, 0, 0))
    for x in range(32, 64):
        for y in range(64):
            half.putpixel((x, y), (255, 255, 255))
    h = ahash(half)
    check("同一图距离为 0", dist(h, ahash(half)) == 0)
    check("明暗图与纯黑距离大", dist(h, a) > 60, f"dist={dist(h, a)}")
    # zip 会在短串处截断（ahash 恒为等长 256 位，故生产路径不受影响）
    check("dist 长度不等时按短串截断", dist("101", "1") == 0, f"dist={dist('101', '1')}")
    check("ahash 支持自定义尺寸", len(ahash(solid((1, 2, 3)), size=8)) == 64)
    PIL_OK = True
except ImportError as e:  # 没装 Pillow 时跳过，不让 CI 因可选依赖红
    PIL_OK = False
    print("SKIP 感知哈希测试（缺少 Pillow: %s）" % e)

# ---------- 5. 封面标题折行：不能在词中间硬断 ----------
st = wx_publish.split_title

check("短标题单行", st("短标题") == ["短标题"], str(st("短标题")))
check("空标题不崩", st("") == [""] and st(None) == [""])

two = st("公众号排版，其实可以全自动")
check("优先在标点后断开", two == ["公众号排版，", "其实可以全自动"], str(two))
check("两行长度均衡（差值≤3）", abs(len(two[0]) - len(two[1])) <= 3, f"{len(two[0])}/{len(two[1])}")

nop = st("标题没有标点但是特别特别长的一句话需要处理")
check("无标点按中点断", len(nop) == 2 and abs(len(nop[0]) - len(nop[1])) <= 2, str(nop))

long_one = st("超" * 40)
check("单行超长截断加省略号",
      all(len(ln) <= 14 for ln in long_one) and long_one[1].endswith("…"), str(long_one)[:40])

check("折行后拼回原文（未截断时）", "".join(two) == "公众号排版，其实可以全自动")

# ---------- 6. 字体探测与兜底（无凭证也能出封面） ----------
font = wx_publish.detect_font()
check("detect_font 返回字符串", isinstance(font, str), font or "(空)")
check("探测到的字体真实存在", (font == "") or os.path.exists(font), font)

try:
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (100, 40), (0, 0, 0))
    d = ImageDraw.Draw(img)
    f = wx_publish._load_font(24)
    check("_load_font 恒返回可用字体对象", f is not None)
    w = wx_publish._text_width(d, "测试文本", f, 24)
    check("_text_width 返回正数", isinstance(w, (int, float)) and w > 0, f"w={w}")

    tmpdir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_tmp_cover")
    os.makedirs(tmpdir, exist_ok=True)
    cover = wx_publish.make_cover("无凭证也能生成封面，验证兜底逻辑", os.path.join(tmpdir, "c.jpg"))
    check("make_cover 无凭证可生成", os.path.getsize(cover) > 3000, f"{os.path.getsize(cover)}B")
    from PIL import Image as _I
    with _I.open(cover) as im:
        check("封面尺寸 900x383", im.size == (900, 383), str(im.size))
    os.remove(cover)
    os.rmdir(tmpdir)
except ImportError:
    print("SKIP 封面测试（缺少 Pillow）")

# ---------- 7. 视频模板回归（与 test_video_iframe.py 互补：只看参数透传） ----------
vf = video_iframe("wxv_1", "0.75", 800, "https://mmbiz.qpic.cn/c.jpg")
check("video_iframe 参数全部透传",
      "wxv_1" in vf and 'data-ratio="0.75"' in vf and 'data-w="800"' in vf
      and "https://mmbiz.qpic.cn/c.jpg" in vf)
check("video_iframe 无明文 http", "http://" not in vf)

failed = [c for c in checks if not c["pass"]]
for c in checks:
    print(("PASS" if c["pass"] else "FAIL"), c["name"], c["detail"])
result = {"ok": not failed, "total": len(checks), "failed": len(failed),
          "pillow": PIL_OK}
print(json.dumps(result, ensure_ascii=False))
sys.exit(0 if not failed else 1)
