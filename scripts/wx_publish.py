# -*- coding: utf-8 -*-
"""微信公众号草稿箱自动化 · 主入口
子命令:
  status                        验证凭证+素材库统计（冒烟用）
  publish <html> --title T [--author A] [--digest D] [--cover JPG] [--dry-run]
                                [--video wxv_XXX --video-ratio 0.8 --video-w 1200 --video-cover ENC]
                                排版好的 HTML 进草稿箱（可自动嵌视频）
  draft-list [N]                草稿箱最新 N 篇
  draft-get <media_id> [--check] 拉草稿（--check 附乱码/视频检验）
  update <media_id> <html> --title T [--author A] [--digest D] [--cover JPG] [--dry-run]
                                [--video wxv_XXX ...]
                                全量更新草稿（显式 UTF-8，防乱码）
  video-add <mp4> --title T [--desc D]   上传视频到素材库
  video-list                    素材库视频列表
所有命令成功时最后输出机读行 {"ok": true, ...}；失败输出 {"ok": false, "error": ..., "errcode": ...} 并退出码 1

本地校验（先于任何网络请求）：文件不存在/编码非 UTF-8/空文件/空标题/标题超 64 字/封面缺失，都会直接报错退出。
--dry-run 只跑本地校验并输出将发送的内容摘要（含视频插入位置），不消耗任何接口调用。

凭证配置（二选一，必须配一项）:
  1. 环境变量  WECHAT_APP_ID / WECHAT_APP_SECRET
  2. 配置文件  config.json（参考 config.example.json，放在脚本同目录或当前目录）
"""
import sys, os, json, argparse, datetime, tempfile

# Windows 控制台默认 cp1252/GBK，中文 --help/输出会 UnicodeEncodeError，强制 UTF-8
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8")
        except Exception:
            pass

BASE = os.path.dirname(os.path.abspath(__file__))


def load_config():
    cfg = {}
    for cand in (os.path.join(BASE, "config.json"), os.path.join(os.getcwd(), "config.json")):
        if os.path.exists(cand):
            with open(cand, encoding="utf-8") as f:
                cfg = json.load(f)
            break
    cfg["app_id"] = os.environ.get("WECHAT_APP_ID") or cfg.get("app_id", "")
    cfg["app_secret"] = os.environ.get("WECHAT_APP_SECRET") or cfg.get("app_secret", "")
    if not cfg["app_id"] or not cfg["app_secret"]:
        print(json.dumps({"ok": False,
                          "error": "缺少公众号凭证：请设置环境变量 WECHAT_APP_ID / WECHAT_APP_SECRET，"
                                   "或在脚本目录放置 config.json（参考 config.example.json）"},
                         ensure_ascii=False))
        sys.exit(1)
    return cfg


CFG = {}
APPID = ""
SECRET = ""
DEFAULT_AUTHOR = "小编"
BRAND_FOOTER = "公众号自动化"
FONT_PATH = ""

# 中文字体候选：Windows 微软雅黑 / macOS 苹方·冬青黑体 / Linux 文泉驿·Noto
FONT_CANDIDATES = (
    r"C:\Windows\Fonts\msyhbd.ttc", r"C:\Windows\Fonts\msyh.ttc",
    "/System/Library/Fonts/PingFang.ttc", "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
)


def detect_font():
    """探测系统中可用的中文字体，找不到返回空串（调用方需兜底）"""
    return next((p for p in FONT_CANDIDATES if os.path.exists(p)), "")


def _load_font(size):
    """加载字体：优先配置/探测到的中文字体，失败退回 PIL 内置字体（英文可用，中文可能缺字）"""
    from PIL import ImageFont
    if FONT_PATH:
        try:
            return ImageFont.truetype(FONT_PATH, size)
        except Exception:
            pass
    try:
        return ImageFont.load_default(size=size)
    except Exception:
        return ImageFont.load_default()


def _text_width(draw, text, font, size):
    """测量文本宽度：textlength → getbbox → 估算，逐级兜底，保证封面生成不因字体崩掉"""
    try:
        return draw.textlength(text, font=font)
    except Exception:
        pass
    try:
        box = draw.textbbox((0, 0), text, font=font)
        return box[2] - box[0]
    except Exception:
        return len(text) * size * 0.5


def init_credentials():
    """延迟加载：--help 等本地操作不要求凭证，真正调 API 的命令才校验"""
    global APPID, SECRET, DEFAULT_AUTHOR, BRAND_FOOTER, FONT_PATH
    cfg = {}
    for cand in (os.path.join(BASE, "config.json"), os.path.join(os.getcwd(), "config.json")):
        if os.path.exists(cand):
            with open(cand, encoding="utf-8") as f:
                cfg = json.load(f)
            break
    cfg["app_id"] = os.environ.get("WECHAT_APP_ID") or cfg.get("app_id", "")
    cfg["app_secret"] = os.environ.get("WECHAT_APP_SECRET") or cfg.get("app_secret", "")
    if not cfg["app_id"] or not cfg["app_secret"]:
        die("缺少公众号凭证：请设置环境变量 WECHAT_APP_ID / WECHAT_APP_SECRET，"
            "或在脚本目录放置 config.json（参考 config.example.json）")
    APPID = cfg["app_id"]
    SECRET = cfg["app_secret"]
    DEFAULT_AUTHOR = cfg.get("author", "小编")
    BRAND_FOOTER = cfg.get("brand_footer", "公众号自动化")
    FONT_PATH = cfg.get("font_path") or detect_font()

REQUESTS_OK = True
try:
    import requests
except ImportError:
    REQUESTS_OK = False


def die(msg, **kw):
    print(json.dumps({"ok": False, "error": msg, **kw}, ensure_ascii=False))
    sys.exit(1)


def ok(**kw):
    print(json.dumps({"ok": True, **kw}, ensure_ascii=False))


def api_check(d, action):
    """微信接口统一错误检查。

    必须显式判 errcode：微信失败时通常**不带**业务字段（如 draft/get 报错时没有 news_item），
    直接 .get(..., [{}]) 取值会得到空结果并误报 ok:true —— 工具自己的冒烟命令也会说谎。
    """
    code = d.get("errcode", 0)
    if code != 0:
        die("%s失败" % action, errcode=code, errmsg=d.get("errmsg", ""))
    return d


def read_html(path):
    """读本地 HTML：友好报错 + 编码兜底（Windows 用户从 WPS/Word 导出的常是 GB18030）"""
    if not os.path.exists(path):
        die("HTML 文件不存在", path=path)
    if os.path.isdir(path):
        die("给的是目录，需要 HTML 文件", path=path)
    try:
        with open(path, "rb") as f:
            raw = f.read()
    except OSError as e:
        die("HTML 文件读取失败", path=path, reason=str(e))
    for enc in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        die("无法识别文件编码（已尝试 UTF-8 / GB18030），请另存为 UTF-8", path=path)
    if not text.strip():
        die("HTML 文件是空的", path=path)
    return text


def check_title(title):
    """微信标题上限 64 字；空标题在服务端才报错，本地先拦，省掉一次封面上传"""
    t = (title or "").strip()
    if not t:
        die("标题不能为空（--title）")
    if len(t) > 64:
        die("标题超过微信上限 64 字", length=len(t))
    return t


def norm_digest(digest, title):
    """摘要上限 120 字：超长自动截断并在 stderr 提示，不阻断发布"""
    d = (digest or "").strip() or title[:50]
    if len(d) > 120:
        sys.stderr.write("[warn] 摘要超过 120 字，已自动截断（原 %d 字）\n" % len(d))
        d = d[:120]
    return d


def check_cover(path):
    """显式指定封面时，本地先确认文件存在且非空，避免白跑一次 token + 上传"""
    if not path:
        return ""
    if not os.path.exists(path):
        die("封面文件不存在", path=path)
    if os.path.getsize(path) == 0:
        die("封面文件是空的", path=path)
    return path


def get_token():
    r = requests.get("https://api.weixin.qq.com/cgi-bin/token",
                     params={"grant_type": "client_credential", "appid": APPID, "secret": SECRET}, timeout=15)
    d = r.json()
    if "access_token" not in d:
        die("获取token失败", detail=d)
    return d["access_token"]


def wx_post_json(url, payload):
    """微信草稿接口必须: 显式 UTF-8 + application/json（requests json= 会产生 \\u 转义导致乱码）"""
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    r = requests.post(url, data=body, headers={"Content-Type": "application/json"}, timeout=60)
    # 显式 UTF-8 解码：微信 content-type 不带 charset 时 r.json() 按 ISO-8859-1 误读，返回值中文全变假乱码
    return json.loads(r.content.decode("utf-8"))


TITLE_PUNCT = "，。、；：！？,;:!?）)】》」』…—"


def split_title(title, max_chars=12):
    """封面标题折行：优先在标点后断开，避免把词拆成两半（如「全自/动」）。

    规则：
      - 不超过 max_chars 字 → 单行
      - 否则两行，断点取「中点附近」的标点之后；无标点则取中点
      - 每行超过 max_chars+2 字时截断加省略号（防止溢出 900px 画布）
    """
    title = (title or "").strip()
    if not title:
        return [""]
    if len(title) <= max_chars:
        return [title]

    mid = len(title) // 2
    best = None
    for i, ch in enumerate(title):
        if ch in TITLE_PUNCT:
            cut = i + 1
            if 3 <= cut <= len(title) - 1:
                if best is None or abs(cut - mid) < abs(best - mid):
                    best = cut
    if best is None:
        best = mid if len(title) <= max_chars * 2 else max_chars

    lines = [title[:best], title[best:]]
    limit = max_chars + 2
    return [ln if len(ln) <= limit else ln[:limit - 1] + "…" for ln in lines]


def make_cover(title, out_path):
    from PIL import Image, ImageDraw
    W, H = 900, 383
    img = Image.new("RGB", (W, H), (24, 48, 92))
    d = ImageDraw.Draw(img)
    d.rectangle([0, H - 70, W, H], fill=(200, 60, 50))
    for i in range(5):
        d.ellipse([W - 320 + i * 70, -120 + i * 55, W - 80 + i * 70, 130 + i * 55], outline=(255, 255, 255), width=3)
    font_big = _load_font(64)
    font_small = _load_font(30)
    lines = split_title(title)
    y = 110 if len(lines) == 1 else 95
    for ln in lines[:2]:
        w = _text_width(d, ln, font_big, 64)
        d.text(((W - w) / 2, y), ln, font=font_big, fill=(255, 255, 255))
        y += 90
    footer = BRAND_FOOTER
    w = _text_width(d, footer, font_small, 30)
    d.text(((W - w) / 2, H - 52), footer, font=font_small, fill=(255, 255, 255))
    img.save(out_path, "JPEG", quality=90)
    return out_path


def upload_material(token, path, mtype, description=None):
    mime = "image/jpeg" if mtype == "image" else "video/mp4" if mtype == "video" else "application/octet-stream"
    data = {"description": json.dumps(description, ensure_ascii=False).encode("utf-8")} if description else None
    # 用 with 显式关闭：否则文件句柄悬挂，Windows 下会锁住文件（下次覆盖 auto_cover 时报 PermissionError）
    with open(path, "rb") as fh:
        r = requests.post(f"https://api.weixin.qq.com/cgi-bin/material/add_material?access_token={token}&type={mtype}",
                          files={"media": (os.path.basename(path), fh, mime)}, data=data, timeout=120)
    return json.loads(r.content.decode("utf-8"))


def upload_thumb(token, jpg_path):
    d = upload_material(token, jpg_path, "image")
    if "media_id" not in d:
        die("上传封面失败", detail=d)
    return d["media_id"], d.get("url", "")


def add_draft(token, title, content_html, thumb_media_id, digest, author=None):
    d = wx_post_json(f"https://api.weixin.qq.com/cgi-bin/draft/add?access_token={token}",
                     {"articles": [{"title": title, "author": author or DEFAULT_AUTHOR, "digest": digest,
                                    "content": content_html, "thumb_media_id": thumb_media_id,
                                    "need_open_comment": 1, "only_fans_can_comment": 0}]})
    if d.get("errcode", 0) != 0:
        die("创建草稿失败", detail=d)
    return d["media_id"]


def update_draft(token, media_id, title, content_html, thumb_media_id, digest, author=None):
    d = wx_post_json(f"https://api.weixin.qq.com/cgi-bin/draft/update?access_token={token}",
                     {"media_id": media_id, "index": 0,
                      "articles": {"title": title, "author": author or DEFAULT_AUTHOR, "digest": digest,
                                   "content": content_html, "thumb_media_id": thumb_media_id,
                                   "need_open_comment": 1, "only_fans_can_comment": 0}})
    return d


def video_iframe(wxv_id, ratio, width, cover_enc):
    """微信原生视频播放器模板（wxv_ 前缀 ID，从后台插入的真品复刻）。
    wxv id 获取：视频在后台编辑器插入一次 -> draft/get 拉回 -> 提取 data-mpvid。"""
    return ('<section nodeleaf=""><iframe class="video_iframe rich_pages" '
            'data-src="https://mp.weixin.qq.com/mp/readtemplate?t=pages/video_player_tmpl&amp;action=mpvideo&amp;auto=0&amp;vid=%s" '
            'data-mpvid="%s" data-vidtype="2" data-cover="%s" data-ratio="%s" data-w="%d"></iframe></section>'
            ) % (wxv_id, wxv_id, cover_enc, ratio, width)


def garble_check(content):
    return {"u_escape": content.count("\\u"), "double_encode": content.count("Ã"),
            "replacement_char": content.count("\ufffd")}


def cmd_status(args):
    if not REQUESTS_OK:
        die("requests 未安装")
    token = get_token()
    r = requests.post(f"https://api.weixin.qq.com/cgi-bin/material/batchget_material?access_token={token}",
                      data=json.dumps({"type": "video", "offset": 0, "count": 1}), timeout=30)
    d = api_check(json.loads(r.content.decode("utf-8")), "素材库查询")
    ok(token="ok", video_materials=d.get("item_count", 0), appid=APPID)


def inject_video(html, wxv_id, ratio, width, cover):
    """把视频 iframe 插到第一个 </h2> 之后；没有 h2 就插到正文最前"""
    iframe = video_iframe(wxv_id, ratio, width, cover or "")
    idx = html.find("</h2>")
    if idx > 0:
        ins = idx + len("</h2>")
        return html[:ins] + iframe + html[ins:], "after_h2"
    return iframe + html, "top"


def cmd_publish(args):
    # 先做本地校验，再取 token：本地文件有问题不该白跑一次网络请求
    title = check_title(args.title)
    html = read_html(args.html)
    cover = check_cover(args.cover)
    digest = norm_digest(args.digest, title)
    video_at = None
    if args.video:
        html, video_at = inject_video(html, args.video, args.video_ratio, args.video_w, args.video_cover)

    if getattr(args, "dry_run", False):
        ok(dry_run=True, title=title, digest=digest, content_length=len(html),
           video_at=video_at, cover=cover or "(将自动生成)", media_id=None)
        return

    token = get_token()
    cover = cover or make_cover(title, os.path.join(tempfile.gettempdir(), "wx_auto_cover.jpg"))
    thumb_id, _ = upload_thumb(token, cover)
    mid = add_draft(token, title, html, thumb_id, digest, args.author)
    ok(media_id=mid, title=title, cover=cover, content_length=len(html), video_at=video_at)


def cmd_draft_list(args):
    token = get_token()
    r = requests.post(f"https://api.weixin.qq.com/cgi-bin/draft/batchget?access_token={token}",
                      data=json.dumps({"offset": 0, "count": args.count, "no_content": 1}).encode("utf-8"), timeout=30)
    d = api_check(json.loads(r.content.decode("utf-8")), "拉取草稿列表")
    items = [{"title": it["content"]["news_item"][0].get("title", ""),
              "media_id": it.get("media_id", ""),
              "updated": datetime.datetime.fromtimestamp(it.get("update_time", 0)).strftime("%m-%d %H:%M")}
             for it in d.get("item", [])]
    ok(total=d.get("total_count", 0), drafts=items)


def cmd_draft_get(args):
    token = get_token()
    r = requests.post(f"https://api.weixin.qq.com/cgi-bin/draft/get?access_token={token}",
                      data=json.dumps({"media_id": args.media_id}).encode("utf-8"), timeout=30)
    # 显式 UTF-8 解码：微信 content-type 无 charset，r.json() 会按 ISO-8859-1 误读出假乱码
    d = api_check(json.loads(r.content.decode("utf-8")), "拉取草稿")
    n = d.get("news_item", [{}])[0]
    c = n.get("content", "")
    info = {"ok": True, "title": n.get("title", ""), "content_length": len(c),
            "tables_th": c.count("<th"), "h2": c.count("<h2"),
            "iframe_video": c.count("<iframe"), "mpvideo": c.count("<mpvideo"),
            "img_mmbiz": c.count("mmbiz.qpic.cn")}
    if args.check:
        info["garble"] = garble_check(c)
    print(json.dumps(info, ensure_ascii=False))


def cmd_update(args):
    title = check_title(args.title)
    html = read_html(args.html)
    cover = check_cover(args.cover)
    digest = norm_digest(args.digest, title)
    video_at = None
    if getattr(args, "video", ""):
        html, video_at = inject_video(html, args.video, args.video_ratio, args.video_w, args.video_cover)

    if getattr(args, "dry_run", False):
        ok(dry_run=True, media_id=args.media_id, title=title, digest=digest,
           content_length=len(html), video_at=video_at, cover=cover or "(将自动生成)")
        return

    token = get_token()
    cover = cover or make_cover(title, os.path.join(tempfile.gettempdir(), "wx_auto_cover.jpg"))
    thumb_id, _ = upload_thumb(token, cover)
    d = update_draft(token, args.media_id, title, html, thumb_id, digest, args.author)
    api_check(d, "更新草稿")
    ok(media_id=args.media_id, updated=True, content_length=len(html), video_at=video_at)


def cmd_video_add(args):
    token = get_token()
    desc = {"title": args.title, "introduction": args.desc or ""}
    d = upload_material(token, args.mp4, "video", desc)
    if "media_id" not in d:
        die("上传视频失败", detail=d)
    r = requests.post(f"https://api.weixin.qq.com/cgi-bin/material/get_material?access_token={token}",
                      data=json.dumps({"media_id": d["media_id"]}).encode("utf-8"), timeout=30)
    g = api_check(json.loads(r.content.decode("utf-8")), "查询视频详情")
    # 只输出一行结果：多行 JSON 会破坏「最后一行是机读结果」的约定
    ok(media_id=d["media_id"], vid=g.get("vid", ""), cover_url=g.get("cover_url", ""),
       note="vid 为 apiv_ 前缀，嵌正文需后台插入一次换取 wxv_ id")


def cmd_video_list(args):
    token = get_token()
    r = requests.post(f"https://api.weixin.qq.com/cgi-bin/material/batchget_material?access_token={token}",
                      data=json.dumps({"type": "video", "offset": 0, "count": 20}).encode("utf-8"), timeout=30)
    d = api_check(json.loads(r.content.decode("utf-8")), "拉取视频列表")
    items = [{"media_id": it.get("media_id", ""), "name": it.get("name", ""),
              "updated": datetime.datetime.fromtimestamp(it.get("update_time", 0)).strftime("%m-%d %H:%M")}
             for it in d.get("item", [])]
    ok(total=d.get("item_count", 0), videos=items)


def main():
    p = argparse.ArgumentParser(description="微信公众号草稿箱自动化")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status").set_defaults(func=cmd_status)
    sp = sub.add_parser("publish")
    sp.add_argument("html", help="排版好的 HTML 文件路径")
    sp.add_argument("--title", required=True, help="文章标题（≤64 字）")
    sp.add_argument("--author", default="", help="作者，默认取配置 author")
    sp.add_argument("--digest", default="", help="摘要（≤120 字，超长自动截断；默认取标题前 50 字）")
    sp.add_argument("--cover", default="", help="封面 JPG 路径，不传则按标题自动生成 900x383")
    sp.add_argument("--video", default="", help="wxv_ 前缀视频 id，自动插到第一个 h2 之后")
    sp.add_argument("--video-ratio", default="0.8", help="视频宽高比，默认 0.8")
    sp.add_argument("--video-w", type=int, default=1200, help="视频容器宽度，默认 1200")
    sp.add_argument("--video-cover", default="", help="视频封面 URL（需 URL 编码）")
    sp.add_argument("--dry-run", action="store_true", help="只做本地校验并输出将要发送的内容摘要，不调用任何接口")
    sp.set_defaults(func=cmd_publish)
    sp = sub.add_parser("draft-list"); sp.add_argument("count", nargs="?", type=int, default=5, help="拉取条数，默认 5")
    sp.set_defaults(func=cmd_draft_list)
    sp = sub.add_parser("draft-get"); sp.add_argument("media_id"); sp.add_argument("--check", action="store_true", help="附乱码三指标与结构自检")
    sp.set_defaults(func=cmd_draft_get)
    sp = sub.add_parser("update")
    sp.add_argument("media_id", help="要更新的草稿 media_id")
    sp.add_argument("html", help="新的 HTML 文件路径")
    sp.add_argument("--title", required=True, help="文章标题（≤64 字）")
    sp.add_argument("--author", default="")
    sp.add_argument("--digest", default="", help="摘要（≤120 字）")
    sp.add_argument("--cover", default="", help="封面 JPG，不传则自动生成")
    sp.add_argument("--video", default="", help="wxv_ 前缀视频 id，自动插到第一个 h2 之后")
    sp.add_argument("--video-ratio", default="0.8"); sp.add_argument("--video-w", type=int, default=1200)
    sp.add_argument("--video-cover", default="")
    sp.add_argument("--dry-run", action="store_true", help="只做本地校验，不调用任何接口")
    sp.set_defaults(func=cmd_update)
    sp = sub.add_parser("video-add"); sp.add_argument("mp4", help="本地 mp4 路径")
    sp.add_argument("--title", required=True); sp.add_argument("--desc", default="")
    sp.set_defaults(func=cmd_video_add)
    sub.add_parser("video-list").set_defaults(func=cmd_video_list)
    args = p.parse_args()
    init_credentials()
    args.func(args)


if __name__ == "__main__":
    main()
