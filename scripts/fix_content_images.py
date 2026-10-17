# -*- coding: utf-8 -*-
"""修复 v2:aHash 感知哈希配对(素材接口重压缩后像素不变) -> uploadimg 换正文可用 URL
用法: python fix_content_images.py --dir <html和jpg所在目录> [--files a.html,b.html]
凭证从环境变量 WECHAT_APP_ID / WECHAT_APP_SECRET 或 config.json 读取（参考 config.example.json）"""
import os, re, json, argparse, sys, requests
from PIL import Image

OUT = os.getcwd()


def load_creds():
    base = os.path.dirname(os.path.abspath(__file__))
    cfg = {}
    for cand in (os.path.join(base, "config.json"), os.path.join(OUT, "config.json")):
        if os.path.exists(cand):
            with open(cand, encoding="utf-8") as f:
                cfg = json.load(f)
            break
    appid = os.environ.get("WECHAT_APP_ID") or cfg.get("app_id", "")
    secret = os.environ.get("WECHAT_APP_SECRET") or cfg.get("app_secret", "")
    if not appid or not secret:
        print(json.dumps({"ok": False,
                          "error": "缺少公众号凭证：请设置 WECHAT_APP_ID / WECHAT_APP_SECRET 或 config.json"},
                         ensure_ascii=False))
        sys.exit(1)
    return appid, secret


def ahash(img, size=16):
    g = img.convert("L").resize((size, size), Image.LANCZOS)
    px = list(g.getdata())
    avg = sum(px) / len(px)
    return "".join("1" if p > avg else "0" for p in px)


def dist(a, b):
    return sum(x != y for x, y in zip(a, b))


def get_token(appid, secret):
    d = requests.get("https://api.weixin.qq.com/cgi-bin/token",
                     params={"grant_type": "client_credential", "appid": appid, "secret": secret}, timeout=15).json()
    assert "access_token" in d, d
    return d["access_token"]


def uploadimg(token, path):
    with open(path, "rb") as f:
        r = requests.post(f"https://api.weixin.qq.com/cgi-bin/media/uploadimg?access_token={token}",
                          files={"media": (os.path.basename(path), f, "image/jpeg")}, timeout=60).json()
    assert "url" in r, r
    return r["url"].replace("http://", "https://")


def main():
    ap = argparse.ArgumentParser(description="正文图片 aHash 配对修复")
    ap.add_argument("--dir", default=OUT, help="html 与本地 jpg 所在目录")
    ap.add_argument("--files", default="", help="逗号分隔的 html 文件名；缺省=目录内全部 html")
    ap.add_argument("--max-dist", type=int, default=10, help="aHash 汉明距离阈值")
    args = ap.parse_args()
    os.chdir(args.dir)
    appid, secret = load_creds()
    token = get_token(appid, secret)

    files = [f.strip() for f in args.files.split(",") if f.strip()] if args.files else \
        [f for f in os.listdir(".") if f.endswith(".html")]

    local = {}
    for f in os.listdir("."):
        if f.endswith(".jpg"):
            try:
                local[f] = ahash(Image.open(f))
            except Exception as e:
                print(json.dumps({"warn": f, "err": str(e)[:60]}, ensure_ascii=False))
    all_urls = set()
    htmls = {}
    for f in files:
        html = open(f, encoding="utf-8").read()
        htmls[f] = html
        all_urls |= set(re.findall(r'https?://mmbiz\.qpic\.cn[^"\']+', html))
    mapping = {}; unmatched = []; uploaded = {}
    for u in sorted(all_urls):
        try:
            r = requests.get(u, timeout=30)
            h = ahash(Image.open(__import__("io").BytesIO(r.content)))
        except Exception:
            unmatched.append(u); continue
        best, bd = None, 999
        for f, lh in local.items():
            d = dist(h, lh)
            if d < bd:
                best, bd = f, d
        if best is not None and bd <= args.max_dist:
            if best not in uploaded:
                uploaded[best] = uploadimg(token, best)
            mapping[u] = uploaded[best]
            print(json.dumps({"ok": True, "match": best, "dist": bd, "new": uploaded[best][:70]}, ensure_ascii=False))
        else:
            unmatched.append(u)
    total = 0
    for f, html in htmls.items():
        n = 0
        for old, new in mapping.items():
            if old in html:
                n += html.count(old)
                html = html.replace(old, new)
        open(f.replace(".html", "_fix.html"), "w", encoding="utf-8").write(html)
        total += n
        print(json.dumps({"ok": True, "file": f, "replaced": n}, ensure_ascii=False))
    print(json.dumps({"ok": True, "step": "done", "mapping": len(mapping), "total_replaced": total,
                      "unmatched": [u[:70] for u in unmatched]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
