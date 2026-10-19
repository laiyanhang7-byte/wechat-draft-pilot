#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 templates/ 里的模板发成公众号草稿（供人工验收）。

流程：
  1. 取 template.html 的 <body> 内容，删掉 <script>（公众号正文禁止脚本）
  2. 内联族（inline）直接可用；网页级（css-var）默认拒绝——样式会被微信剥成白文
  3. 外链插画逐张上传到公众号正文图床（media/uploadimg），把 src 换成 mmbiz 地址
     上传结果缓存在 assets/uploaded.json，重跑不重复上传
  4. 建草稿 → 自动验收（乱码/h2/配图/标题）→ 桌面生成预览
  5. 输出 media_id 与验收明细

用法:
  python templates/publish_template.py --slug chuli-fenfa --dry-run     # 只准备，不联网
  python templates/publish_template.py --slug chuli-fenfa               # 真发草稿
  python templates/publish_template.py --all                            # 10 套全发
"""
import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "scripts"))

import wx_publish as wx  # noqa: E402

CACHE_NAME = "uploaded.json"


def load_spec(slug):
    with open(os.path.join(HERE, slug, "theme.json"), encoding="utf-8") as f:
        return json.load(f)


def body_of(html):
    """取 <body> 内容；没有 body 就用全文。删掉 script（公众号禁止脚本）"""
    m = re.search(r"<body[^>]*>(.*)</body>", html, re.S | re.I)
    inner = m.group(1) if m else html
    inner = re.sub(r"<script\b[^>]*>.*?</script>", "", inner, flags=re.S | re.I)
    return inner.strip()


def load_cache(slug):
    p = os.path.join(HERE, slug, "assets", CACHE_NAME)
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_cache(slug, cache):
    p = os.path.join(HERE, slug, "assets", CACHE_NAME)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)
        f.write("\n")


def mime_of(path):
    ext = os.path.splitext(path)[1].lower()
    return {".png": "image/png", ".gif": "image/gif", ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg", ".webp": "image/webp"}.get(ext, "image/png")


def upload_image(token, path):
    """正文图片上传（media/uploadimg）：返回 https 的 mmbiz 地址"""
    import requests
    with open(path, "rb") as f:
        r = requests.post(
            "https://api.weixin.qq.com/cgi-bin/media/uploadimg",
            params={"access_token": token},
            files={"media": (os.path.basename(path), f, mime_of(path))},
            timeout=120)
    d = wx.api_check(json.loads(r.content.decode("utf-8")), "上传正文图片")
    if "url" not in d:
        wx.die("上传正文图片失败：响应无 url", detail=d)
    return d["url"].replace("http://", "https://")


def prepare(slug, dry_run=False, token=None, allow_css_var=False):
    """返回 (html, stats)。dry_run 时不上传，只统计。"""
    spec = load_spec(slug)
    if spec["kind"] == "css-var" and not allow_css_var:
        raise SystemExit(
            "[%s] 是网页级模板（<style> + CSS 变量），公众号会剥掉样式，发上去是白文。\n"
            "如确认要发（仅用于看结构），加 --allow-css-var。" % slug)

    with open(os.path.join(HERE, slug, "template.html"), encoding="utf-8") as f:
        html = body_of(f.read())

    cache = load_cache(slug)
    stats = {"slug": slug, "images_total": 0, "images_uploaded": 0,
             "images_cached": 0, "images_missing": 0, "replaced": 0}

    for item in spec["images"]:
        url = item["url"]
        rel = item.get("file") or ""
        local = os.path.join(HERE, slug, rel) if rel else ""
        stats["images_total"] += 1
        if not local or not os.path.exists(local):
            stats["images_missing"] += 1
            continue
        if url in cache:
            new_url = cache[url]
            stats["images_cached"] += 1
        elif dry_run:
            new_url = None
        else:
            new_url = upload_image(token, local)
            cache[url] = new_url
            stats["images_uploaded"] += 1
        if new_url:
            n = html.count(url)
            html = html.replace(url, new_url)
            stats["replaced"] += n

    if not dry_run:
        save_cache(slug, cache)

    # 剩余外链图（未下载/未上传）会导致草稿里裂图，必须显式报出来
    left = re.findall(r'src="(https?://[^"]+)"', html)
    left = [u for u in left if "mmbiz.qpic.cn" not in u]
    stats["external_left"] = len(left)
    return html, stats


def publish_one(slug, dry_run=False, allow_css_var=False):
    spec = load_spec(slug)
    title = spec["name"]
    wx.init_credentials()
    token = None if dry_run else wx.get_token()

    html, stats = prepare(slug, dry_run=dry_run, token=token, allow_css_var=allow_css_var)
    digest = spec["tagline"][:120]
    preview, _ = wx.write_preview(html, title)

    if dry_run:
        return {"ok": True, "dry_run": True, "slug": slug, "title": title,
                "content_length": len(html), "preview": preview, **stats}

    cover = wx.make_cover(title, os.path.join(wx.tempfile.gettempdir(), "wx_cover_%s.jpg" % slug))
    thumb_id, _ = wx.upload_thumb(token, cover)
    mid = wx.add_draft(token, title, html, thumb_id, digest, "华星")

    checks, failed = wx.run_verify(token, mid, html, expect_video=False, title=title)
    return {"ok": not failed, "slug": slug, "title": title, "media_id": mid,
            "preview": preview, "verified": not failed,
            "verify_checks": len(checks),
            "failed": [{k: c[k] for k in ("name", "detail")} for c in failed],
            **stats}


def main():
    ap = argparse.ArgumentParser(description="把模板发成公众号草稿")
    ap.add_argument("--slug", default="", help="模板 slug，如 chuli-fenfa")
    ap.add_argument("--all", action="store_true", help="发全部内联族模板")
    ap.add_argument("--dry-run", action="store_true", help="只准备（不联网、不建草稿）")
    ap.add_argument("--allow-css-var", action="store_true", help="允许发网页级模板（会丢样式）")
    args = ap.parse_args()

    sys.path.insert(0, HERE)
    import extract  # noqa: E402

    if args.all:
        slugs = [s for s, v in extract.TEMPLATES.items() if v[2] == "inline"]
    elif args.slug:
        slugs = [args.slug]
    else:
        ap.error("需要 --slug 或 --all")

    results = []
    for slug in slugs:
        try:
            r = publish_one(slug, dry_run=args.dry_run, allow_css_var=args.allow_css_var)
        except SystemExit as e:
            r = {"ok": False, "slug": slug, "error": str(e)}
        results.append(r)
        print(json.dumps(r, ensure_ascii=False))

    ok = sum(1 for r in results if r.get("ok"))
    print(json.dumps({"ok": ok == len(results), "total": len(results), "ok_count": ok,
                      "failed_count": len(results) - ok}, ensure_ascii=False))
    return 0 if ok == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
