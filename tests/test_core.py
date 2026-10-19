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

# ---------- 8. 本地校验与接口错误处理（防「假成功」回归） ----------
import io, contextlib, tempfile  # noqa: E402


def expect_die(fn):
    """调用 fn，断言它走 die()：输出末行 ok:false 且 SystemExit(1)。返回 (code, payload)"""
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            fn()
    except SystemExit as e:
        lines = [ln for ln in buf.getvalue().strip().splitlines() if ln.strip()]
        return e.code, (json.loads(lines[-1]) if lines else {})
    return None, {}


# 8.1 接口报错必须 fail，不能返回 ok:true（微信失败响应通常不带业务字段，旧代码会误报成功）
code, payload = expect_die(lambda: wx_publish.api_check({"errcode": 40007, "errmsg": "invalid media_id"}, "拉取草稿"))
check("api_check 对 errcode≠0 直接失败", code == 1 and payload.get("ok") is False, str(payload))
check("api_check 透出 errcode/errmsg",
      payload.get("errcode") == 40007 and payload.get("errmsg") == "invalid media_id", str(payload))
check("api_check 对成功响应原样返回",
      wx_publish.api_check({"media_id": "M"}, "x") == {"media_id": "M"})
check("api_check 无 errcode 字段视为成功", wx_publish.api_check({"a": 1}, "x") == {"a": 1})

# 8.2 HTML 读取：缺失/目录/空/GBK/UTF-16 五种情况
tmpd = tempfile.mkdtemp(prefix="wx_test_")


def _write(name, raw):
    p = os.path.join(tmpd, name)
    with open(p, "wb") as f:
        f.write(raw)
    return p


code, payload = expect_die(lambda: wx_publish.read_html(os.path.join(tmpd, "nope.html")))
check("read_html 文件不存在→干净报错", code == 1 and "不存在" in payload.get("error", ""), str(payload))

code, payload = expect_die(lambda: wx_publish.read_html(tmpd))
check("read_html 传目录→报错", code == 1 and "目录" in payload.get("error", ""), str(payload))

code, payload = expect_die(lambda: wx_publish.read_html(_write("empty.html", b"   \n")))
check("read_html 空文件→报错", code == 1 and "空" in payload.get("error", ""), str(payload))

gbk_path = _write("gbk.html", "<p>中文内容</p>".encode("gbk"))
check("read_html 自动识别 GB18030", "中文内容" in wx_publish.read_html(gbk_path))

bom_path = _write("bom.html", "\ufeff<p>带BOM</p>".encode("utf-8"))
check("read_html 正确剥离 UTF-8 BOM", wx_publish.read_html(bom_path).startswith("<p>"), repr(wx_publish.read_html(bom_path)[:8]))

code, payload = expect_die(lambda: wx_publish.read_html(_write("u16.html", "<p>中文</p>".encode("utf-16"))))
check("read_html 无法识别编码时明确报错", code == 1 and "编码" in payload.get("error", ""), str(payload))

# 8.3 标题 / 摘要校验
code, payload = expect_die(lambda: wx_publish.check_title("   "))
check("空标题被本地拦下", code == 1 and "标题" in payload.get("error", ""), str(payload))

code, payload = expect_die(lambda: wx_publish.check_title("字" * 65))
check("标题超 64 字被拦下", code == 1 and payload.get("length") == 65, str(payload))

check("标题去首尾空白", wx_publish.check_title("  正常标题  ") == "正常标题")
check("64 字标题正好放行", wx_publish.check_title("字" * 64) == "字" * 64)

check("摘要缺省取标题前 50 字", wx_publish.norm_digest("", "标" * 80) == "标" * 50)
check("摘要 120 字原样保留", wx_publish.norm_digest("摘" * 120, "t") == "摘" * 120)

_buf = io.StringIO()
with contextlib.redirect_stderr(_buf):
    trimmed = wx_publish.norm_digest("摘" * 150, "t")
check("摘要超 120 字自动截断并提示", len(trimmed) == 120 and "截断" in _buf.getvalue(), f"{len(trimmed)} {_buf.getvalue()!r}")

# 8.4 视频注入位置
h2_html = "<h2>标题</h2><p>正文</p>"
out, where = wx_publish.inject_video(h2_html, "wxv_1", "0.8", 1200, "")
check("有 h2 时插到 </h2> 之后", where == "after_h2" and out.index("<section") > out.index("</h2>"), where)
check("注入不破坏原文", "标题" in out and "正文" in out)

out2, where2 = wx_publish.inject_video("<p>无标题</p>", "wxv_1", "0.8", 1200, "")
check("无 h2 时插到最前", where2 == "top" and out2.startswith("<section"), where2)

# 清理临时目录
for fn in os.listdir(tmpd):
    os.remove(os.path.join(tmpd, fn))
os.rmdir(tmpd)

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
