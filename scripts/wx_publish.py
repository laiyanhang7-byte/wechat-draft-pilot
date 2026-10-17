# -*- coding: utf-8 -*-
"""微信公众号草稿箱自动化 · 主入口
子命令:
  status                        验证凭证+素材库统计（冒烟用）
  publish <html> --title T [--author A] [--digest D] [--cover JPG]
                                [--video wxv_XXX --video-ratio 0.8 --video-w 1200 --video-cover ENC]
                                排版好的 HTML 进草稿箱（可自动嵌视频）
  draft-list [N]                草稿箱最新 N 篇
  draft-get <media_id> [--check] 拉草稿（--check 附乱码/视频检验）
  update <media_id> <html> --title T [--author A] [--digest D] [--cover JPG]
                                全量更新草稿（显式 UTF-8，防乱码）
  video-add <mp4> --title T [--desc D]   上传视频到素材库
  video-list                    素材库视频列表
所有命令成功时最后输出机读行 {"ok": true, ...}

凭证配置（二选一，必须配一项）:
  1. 环境变量  WECHAT_APP_ID / WECHAT_APP_SECRET
  2. 配置文件  config.json（参考 config.example.json，放在脚本同目录或当前目录）
"""
import sys, os, json, argparse, datetime

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
    FONT_PATH = cfg.get("font_path") or next(
        (p for p in (r"C:\Windows\Fonts\msyhbd.ttc", r"C:\Windows\Fonts\msyh.ttc",          # Windows 微软雅黑
                     "/System/Library/Fonts/PingFang.ttc", "/System/Library/Fonts/Hiragino Sans GB.ttc",  # macOS 苹方/冬青黑体
                     "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",                    # Linux 文泉驿
                     "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc")            # Linux Noto
         if os.path.exists(p)), "")

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


def make_cover(title, out_path):
    from PIL import Image, ImageDraw, ImageFont
    W, H = 900, 383
    img = Image.new("RGB", (W, H), (24, 48, 92))
    d = ImageDraw.Draw(img)
    d.rectangle([0, H - 70, W, H], fill=(200, 60, 50))
    for i in range(5):
        d.ellipse([W - 320 + i * 70, -120 + i * 55, W - 80 + i * 70, 130 + i * 55], outline=(255, 255, 255), width=3)
    font_big = ImageFont.truetype(FONT_PATH, 64)
    font_small = ImageFont.truetype(FONT_PATH, 30)
    lines = [title[:12], title[12:24]] if len(title) > 12 else [title]
    y = 110
    for ln in lines[:2]:
        w = d.textlength(ln, font=font_big)
        d.text(((W - w) / 2, y), ln, font=font_big, fill=(255, 255, 255))
        y += 90
    footer = BRAND_FOOTER
    w = d.textlength(footer, font=font_small)
    d.text(((W - w) / 2, H - 52), footer, font=font_small, fill=(255, 255, 255))
    img.save(out_path, "JPEG", quality=90)
    return out_path


def upload_material(token, path, mtype, description=None):
    files = {"media": (os.path.basename(path), open(path, "rb"),
                       "image/jpeg" if mtype == "image" else "video/mp4" if mtype == "video" else "application/octet-stream")}
    data = {"description": json.dumps(description, ensure_ascii=False).encode("utf-8")} if description else None
    r = requests.post(f"https://api.weixin.qq.com/cgi-bin/material/add_material?access_token={token}&type={mtype}",
                      files=files, data=data, timeout=120)
    return r.json()


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
    d = r.json()
    ok(token="ok", video_materials=d.get("item_count", 0), appid=APPID)


def cmd_publish(args):
    token = get_token()
    html = open(args.html, encoding="utf-8").read()
    if args.video:
        # 视频插入：第一个 h2 结束后，或正文最前
        iframe = video_iframe(args.video, args.video_ratio, args.video_w, args.video_cover or "")
        idx = html.find("</h2>")
        if idx > 0:
            ins = idx + len("</h2>")
            html = html[:ins] + iframe + html[ins:]
        else:
            html = iframe + html
    cover = args.cover or make_cover(args.title, os.path.join(BASE, "auto_cover.jpg"))
    thumb_id, _ = upload_thumb(token, cover)
    mid = add_draft(token, args.title, html, thumb_id, args.digest or args.title[:50], args.author)
    ok(media_id=mid, title=args.title, cover=cover)


def cmd_draft_list(args):
    token = get_token()
    r = requests.post(f"https://api.weixin.qq.com/cgi-bin/draft/batchget?access_token={token}",
                      data=json.dumps({"offset": 0, "count": args.count, "no_content": 1}).encode("utf-8"), timeout=30)
    d = r.json()
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
    d = json.loads(r.content.decode("utf-8"))
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
    token = get_token()
    html = open(args.html, encoding="utf-8").read()
    cover = args.cover or make_cover(args.title, os.path.join(BASE, "auto_cover.jpg"))
    thumb_id, _ = upload_thumb(token, cover)
    d = update_draft(token, args.media_id, args.title, html, thumb_id, args.digest or args.title[:50], args.author)
    if d.get("errcode", 0) != 0:
        die("更新草稿失败", detail=d)
    ok(media_id=args.media_id, updated=True)


def cmd_video_add(args):
    token = get_token()
    desc = {"title": args.title, "introduction": args.desc or ""}
    d = upload_material(token, args.mp4, "video", desc)
    if "media_id" not in d:
        die("上传视频失败", detail=d)
    g = requests.post(f"https://api.weixin.qq.com/cgi-bin/material/get_material?access_token={token}",
                      data=json.dumps({"media_id": d["media_id"]}).encode("utf-8"), timeout=30).json()
    ok(media_id=d["media_id"], vid=g.get("vid", ""), note="vid 为 apiv_ 前缀，嵌正文需后台插入一次换取 wxv_ id")
    if g.get("cover_url"):
        ok2 = json.dumps({"ok": True, "cover_url": g["cover_url"]}, ensure_ascii=False)
        print(ok2)


def cmd_video_list(args):
    token = get_token()
    r = requests.post(f"https://api.weixin.qq.com/cgi-bin/material/batchget_material?access_token={token}",
                      data=json.dumps({"type": "video", "offset": 0, "count": 20}).encode("utf-8"), timeout=30)
    d = r.json()
    items = [{"media_id": it.get("media_id", ""), "name": it.get("name", ""),
              "updated": datetime.datetime.fromtimestamp(it.get("update_time", 0)).strftime("%m-%d %H:%M")}
             for it in d.get("item", [])]
    ok(total=d.get("item_count", 0), videos=items)


def main():
    p = argparse.ArgumentParser(description="微信公众号草稿箱自动化")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status").set_defaults(func=cmd_status)
    sp = sub.add_parser("publish")
    sp.add_argument("html"); sp.add_argument("--title", required=True)
    sp.add_argument("--author", default=""); sp.add_argument("--digest", default="")
    sp.add_argument("--cover", default=""); sp.add_argument("--video", default="")
    sp.add_argument("--video-ratio", default="0.8"); sp.add_argument("--video-w", type=int, default=1200)
    sp.add_argument("--video-cover", default="")
    sp.set_defaults(func=cmd_publish)
    sp = sub.add_parser("draft-list"); sp.add_argument("count", nargs="?", type=int, default=5)
    sp.set_defaults(func=cmd_draft_list)
    sp = sub.add_parser("draft-get"); sp.add_argument("media_id"); sp.add_argument("--check", action="store_true")
    sp.set_defaults(func=cmd_draft_get)
    sp = sub.add_parser("update"); sp.add_argument("media_id"); sp.add_argument("html")
    sp.add_argument("--title", required=True); sp.add_argument("--author", default="")
    sp.add_argument("--digest", default=""); sp.add_argument("--cover", default="")
    sp.set_defaults(func=cmd_update)
    sp = sub.add_parser("video-add"); sp.add_argument("mp4"); sp.add_argument("--title", required=True)
    sp.add_argument("--desc", default="")
    sp.set_defaults(func=cmd_video_add)
    sub.add_parser("video-list").set_defaults(func=cmd_video_list)
    args = p.parse_args()
    init_credentials()
    args.func(args)


if __name__ == "__main__":
    main()
