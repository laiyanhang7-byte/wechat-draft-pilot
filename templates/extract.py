#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""模板抽取与校验工具。

把 templates/<slug>/template.html 里的设计规格（配色 / 字体 / 字号 / 结构类 / 插画）
抽成机器可读的 theme.json，并提供 --verify 做一致性对账，防止改模板时悄悄丢东西。

用法:
  python templates/extract.py                  # 抽取并写入 theme.json + registry.json
  python templates/extract.py --verify          # 只校验，不写文件（CI / 提交前用）
  python templates/extract.py --fetch-assets    # 下载插画到 assets/ 并登记指纹（需联网）
  python templates/extract.py --wechat-report   # 输出公众号兼容性报告

校验项（任一不过 → 退出码 1）：
  1. template.html 的 sha256 与 theme.json 记录一致（模板未被偷偷改动）
  2. :root 里每个色值都能在 HTML 中找到
  3. 字体栈与 :root 完全一致
  4. 插画清单双向对齐（HTML 里每个 src 都在清单里，清单里每个都在 HTML 里，次数一致）
  5. 内联 SVG 数量一致
  6. 模板自带说明面板里声明的每个色值，都真实存在于 CSS 变量中
  7. 结构类（.kicker / h1.title 等）在 HTML 中确实被使用
"""
import argparse
import hashlib
import json
import os
import re
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))

# slug → (中文名, 一句话定位, 模板族)
#   css-var : 网页级模板（:root 变量 + <style> 块），需内联或改写才能进公众号
#   inline  : 内联样式模板（样式直接写在元素 style 上），可直接进公众号
TEMPLATES = {
    "cream-magazine": ("奶油杂志风", "大标题杂志排版，适合深度长文、品牌内容、生活方式", "css-var"),
    "dopamine-pop": ("多巴胺撞色风", "高饱和撞色 + 贴纸元素，适合轻松话题、活动种草", "css-var"),
    "forest-natural": ("森系自然风", "低饱和草木色 + 手绘枝丫，适合治愈、自然、慢生活", "css-var"),
    "chuli-fenfa": ("踔厉奋发启新程", "红金商务，适合年度总结、动员大会、开门红", "inline"),
    "light-minimal": ("轻简设计", "留白克制，适合品牌简述、产品介绍、简约风长文", "inline"),
    "rigorous-summary": ("严谨务实总结提升", "蓝灰稳重，适合部门总结、述职报告、工作复盘", "inline"),
    "cohesion-2024": ("凝心聚力2024蓄力前行", "红蓝撞色，适合年会、团队动员、年度规划", "inline"),
    "review-new-ideas": ("回顾总结启新思", "暖橙复古，适合季度回顾、项目复盘、经验沉淀", "inline"),
    "visual-minimal": ("视觉极简", "黑白极简，适合观点输出、深度评论、极简审美", "inline"),
    "year-end-summary": ("年底工作总结", "稳重商务，适合年终总结、绩效汇报、成果展示", "inline"),
}

HEX_RE = re.compile(r"#[0-9A-Fa-f]{3,8}\b")
ROOT_RE = re.compile(r":root\s*\{(.*?)\}", re.S)
VAR_RE = re.compile(r"--([\w-]+)\s*:\s*([^;]+);")
IMG_RE = re.compile(r'<img\b[^>]*?src="([^"]+)"[^>]*>', re.I)
FONT_RE = re.compile(r"font-family\s*:\s*([^;}]+)")
SIZE_RE = re.compile(r"font-size\s*:\s*([^;}]+)")


def sha256_file(path, text=False):
    """内容指纹。

    text=True：按 LF 归一化后计算，避免 Windows 检出成 CRLF 导致误报（仅用于 HTML/JSON 等文本）
    text=False：按原始字节计算，二进制（JPEG 内部也有 0D0A 字节）绝不做归一化
    """
    h = hashlib.sha256()
    with open(path, "rb") as f:
        data = f.read()
    if text:
        data = data.replace(b"\r\n", b"\n")
    h.update(data)
    return h.hexdigest()


def strip_tags(s):
    return re.sub(r"<[^>]+>", "", s).strip()


def parse_root(html):
    """解析 :root 里的 CSS 变量，按值类型分成 colors / fonts / others"""
    m = ROOT_RE.search(html)
    if not m:
        return {}, {}, {}
    colors, fonts, others = {}, {}, {}
    for name, raw in VAR_RE.findall(m.group(1)):
        val = raw.strip()
        if val.startswith("#") or val.lower().startswith(("rgb", "hsl")):
            colors[name] = val
        elif re.search(r"serif|sans|monospace|Microsoft|SimSun|PingFang|Noto|Songti", val, re.I):
            fonts[name] = val
        else:
            others[name] = val
    return colors, fonts, others


def parse_panel(html):
    """解析模板自带的「模板说明」面板：结构类 / 声明的配色 / 声明的字体"""
    m = re.search(r'<aside class="panel".*?</aside>', html, re.S)
    if not m:
        return [], [], []
    panel = m.group(0)
    structure, declared_colors, declared_fonts = [], [], []
    section = ""
    for block in re.findall(r'<div class="(p-sec|cls|sw)">(.*?)</div>', panel, re.S):
        kind, inner = block
        text = strip_tags(inner).replace("\n", " ").strip()
        if kind == "p-sec":
            section = text
            continue
        if kind == "cls":
            code = re.search(r"<code>(.*?)</code>", inner, re.S)
            selector = strip_tags(code.group(1)) if code else ""
            use = strip_tags(re.sub(r"<code>.*?</code>", "", inner, flags=re.S))
            use = use.lstrip("· ").strip()
            structure.append({"selector": selector, "use": use, "section": section})
        elif kind == "sw":
            hexes = HEX_RE.findall(text)
            if hexes:
                declared_colors.append({"text": text, "colors": hexes})
            elif re.search(r"字体|宋体|黑体|Serif|Sans|字重", text, re.I):
                declared_fonts.append(text)
    return structure, declared_colors, declared_fonts


def parse_images(html):
    """插画清单：按 src 聚合出现次数，并记录出现位置（最近的 class 上下文）"""
    images = Counter()
    where = {}
    for m in IMG_RE.finditer(html):
        src = m.group(1)
        if src.startswith("data:"):
            continue
        images[src] += 1
        ctx = html[max(0, m.start() - 80):m.start()]
        cls = re.findall(r'class="([^"]+)"', ctx)
        if src not in where and cls:
            where[src] = cls[-1]
    return images, where


def parse_inline_svg(html):
    """内联 SVG（排除 <link> 里的 data URI favicon）"""
    body = re.sub(r"<link\b[^>]*>", "", html, flags=re.I)
    out = Counter()
    for m in re.finditer(r"<svg\b([^>]*)>", body, re.I):
        cls = re.search(r'class="([^"]+)"', m.group(1))
        out[cls.group(1) if cls else "(无 class)"] += 1
    return out


def parse_external_deps(html):
    urls = set()
    for m in re.finditer(r'(?:href|src)="(https?://[^"]+)"', html, re.I):
        u = m.group(1)
        if "w3.org" in u or "doubaocdn.com" in u:
            continue
        urls.add(u)
    return sorted(urls)


def wechat_issues(html):
    """公众号正文兼容性：这些写法在草稿箱里会被剥掉"""
    issues = []
    if re.search(r"<style\b", html, re.I):
        issues.append("含 <style> 块 —— 公众号正文会剥离，样式需内联到元素 style 属性")
    if re.search(r'<link\b[^>]*rel="stylesheet"', html, re.I):
        issues.append("含外链样式表 —— 公众号不加载，需改用系统字体或内联")
    if re.search(r"var\(--", html):
        issues.append("使用 CSS 变量 var(--x) —— 公众号不支持，需展开为具体值")
    if re.search(r"@media", html):
        issues.append("含 @media 响应式规则 —— 公众号正文不生效（宽度由客户端决定）")
    if re.search(r'<img[^>]+src="https?://(?!mmbiz)', html, re.I):
        issues.append("含外链图片 —— 公众号正文会剥掉外链图，需先上传素材库换成 mmbiz 地址")
    if re.search(r"<script\b", html, re.I):
        issues.append("含 <script> —— 公众号正文禁止脚本，交互面板需删除")
    return issues


def parse_inline_styles(html, top_n=8):
    """内联样式族（小墨鹰系）：样式写在元素 style 属性上，没有 :root 也没有 <style>。

    配色从 style="..." 里出现的色值统计（按频次取前 N），字体同理。
    """
    styles = re.findall(r'style="([^"]*)"', html)
    colors = Counter()
    fonts = Counter()
    sizes = Counter()
    for s in styles:
        for c in re.findall(r"#[0-9A-Fa-f]{3,8}\b", s):
            colors[c.upper() if len(c) == 7 else c] += 1
        for c in re.findall(r"rgba?\([^)]+\)", s):
            colors[c.replace(" ", "")] += 1
        for f in re.findall(r"font-family\s*:\s*([^;\"']+)", s):
            fonts[f.strip()] += 1
        for z in re.findall(r"font-size\s*:\s*(\d+(?:\.\d+)?px)", s):
            sizes[z] += 1
    palette = {}
    for i, (val, _n) in enumerate(colors.most_common(top_n), 1):
        palette["c%d" % i] = val
    font_map = {}
    for i, (val, _n) in enumerate(fonts.most_common(4), 1):
        font_map["f%d" % i] = val
    return palette, font_map, dict(colors), [z for z, _ in sizes.most_common()]


def parse_inline_images(html):
    """内联族的插画：xmyeditor 素材（png/gif 装饰件）"""
    return parse_images(html)


def extract(slug):
    tpl_path = os.path.join(HERE, slug, "template.html")
    if not os.path.exists(tpl_path):
        raise SystemExit("缺少模板文件: %s" % tpl_path)
    with open(tpl_path, encoding="utf-8") as f:
        html = f.read()

    name, tagline, kind = TEMPLATES[slug]
    images, where = parse_images(html)
    svgs = parse_inline_svg(html)

    if kind == "css-var":
        colors, fonts, others = parse_root(html)
        structure, declared_colors, declared_fonts = parse_panel(html)
        all_colors = dict(Counter(HEX_RE.findall(html)).most_common())
        type_scale = sorted({s.strip() for s in SIZE_RE.findall(html) if s.strip().endswith("px")},
                            key=lambda x: -float(x.rstrip("px")))
        font_stacks = sorted({s.strip() for s in FONT_RE.findall(html)})
    else:
        colors, fonts, all_colors, type_scale = parse_inline_styles(html)
        others = {}
        structure, declared_colors, declared_fonts = [], [], []
        font_stacks = sorted({s for s in FONT_RE.findall(html)})

    asset_map = {}
    manifest_path = os.path.join(HERE, slug, "assets", "manifest.json")
    if os.path.exists(manifest_path):
        with open(manifest_path, encoding="utf-8") as f:
            asset_map = {a["url"]: a for a in json.load(f).get("assets", [])}

    image_list = []
    for url, count in sorted(images.items()):
        item = {"url": url, "count": count, "where": where.get(url, "")}
        if url in asset_map:
            item.update({"file": asset_map[url]["file"], "sha256": asset_map[url]["sha256"],
                         "bytes": asset_map[url]["bytes"], "size": asset_map[url]["size"]})
        else:
            item["file"] = ""
        image_list.append(item)

    return {
        "slug": slug,
        "name": name,
        "tagline": tagline,
        "kind": kind,
        "source": "template.html",
        "source_sha256": sha256_file(tpl_path, text=True),
        "source_bytes": os.path.getsize(tpl_path),
        "palette": colors,
        "fonts": fonts,
        "font_note": ("" if fonts else
                      "模板未在样式中指定 font-family，使用公众号默认字体（非缺失）"),
        "other_vars": others,
        "all_hex_colors": all_colors,
        "type_scale": type_scale,
        "font_stacks_used": font_stacks,
        "structure": structure,
        "declared_colors": declared_colors,
        "declared_fonts": declared_fonts,
        "images": image_list,
        "inline_svg": dict(svgs),
        "external_deps": parse_external_deps(html),
        "wechat_issues": wechat_issues(html),
    }


def verify(spec):
    """对账：spec 是刚从 template.html 抽出来的，theme.json 是已登记的"""
    slug = spec["slug"]
    tpl_path = os.path.join(HERE, slug, "template.html")
    with open(tpl_path, encoding="utf-8") as f:
        html = f.read()
    checks = []

    def add(name, ok, detail=""):
        checks.append({"template": slug, "check": name, "pass": bool(ok), "detail": detail})

    json_path = os.path.join(HERE, slug, "theme.json")
    if not os.path.exists(json_path):
        add("theme.json 存在", False, json_path)
        return checks
    with open(json_path, encoding="utf-8") as f:
        saved = json.load(f)

    add("模板指纹未变", saved.get("source_sha256") == spec["source_sha256"],
        "%s vs %s" % (str(saved.get("source_sha256"))[:12], spec["source_sha256"][:12]))
    add("模板族未变", saved.get("kind") == spec["kind"], str(spec["kind"]))
    add("配色变量一致", saved.get("palette") == spec["palette"],
        "登记 %d 色 / 实际 %d 色" % (len(saved.get("palette", {})), len(spec["palette"])))
    add("字体栈一致", saved.get("fonts") == spec["fonts"],
        "%s vs %s" % (list(saved.get("fonts", {}).values()), list(spec["fonts"].values())))

    # 色值比对时忽略空格差异（rgb(255, 255, 255) vs rgb(255,255,255)）
    html_lower = html.lower()
    html_nospace = re.sub(r"\s+", "", html_lower)
    for name, val in spec["palette"].items():
        v = val.lower()
        add("色值 %s 真实存在于 HTML" % val,
            v in html_lower or re.sub(r"\s+", "", v) in html_nospace, name)

    saved_imgs = {i["url"]: i["count"] for i in saved.get("images", [])}
    now_imgs = {i["url"]: i["count"] for i in spec["images"]}
    add("插画清单一致", saved_imgs == now_imgs,
        "登记 %d 张 / 实际 %d 张" % (len(saved_imgs), len(now_imgs)))
    add("插画总数一致", sum(saved_imgs.values()) == sum(now_imgs.values()),
        "%d vs %d" % (sum(saved_imgs.values()), sum(now_imgs.values())))
    add("内联 SVG 一致", saved.get("inline_svg") == spec["inline_svg"],
        "%s vs %s" % (saved.get("inline_svg"), spec["inline_svg"]))

    # 以下两类只对网页级模板（带说明面板）有意义
    if spec["kind"] == "css-var":
        palette_vals = {v.lower() for v in spec["palette"].values()}
        for entry in spec["declared_colors"]:
            for hx in entry["colors"]:
                add("说明面板声明的 %s 在变量表中" % hx, hx.lower() in palette_vals, entry["text"][:30])

        for item in spec["structure"]:
            sel = item["selector"]
            token = sel.split()[-1] if sel else ""
            cls = re.sub(r"^[a-z0-9]+", "", token).lstrip(".")
            if not cls:
                continue
            add("结构类 %s 被使用" % token, ('class="%s' % cls) in html or (" %s" % cls) in html
                or ("%s\"" % cls) in html, item["use"][:24])

    return checks


def write_registry(specs):
    reg = {
        "generated_by": "templates/extract.py",
        "count": len(specs),
        "templates": [{
            "slug": s["slug"],
            "name": s["name"],
            "kind": s["kind"],
            "tagline": s["tagline"],
            "palette": s["palette"],
            "fonts": s["fonts"],
            "images": len(s["images"]),
            "structure_classes": len(s["structure"]),
            "wechat_issues": len(s["wechat_issues"]),
        } for s in specs],
    }
    with open(os.path.join(HERE, "registry.json"), "w", encoding="utf-8") as f:
        json.dump(reg, f, ensure_ascii=False, indent=2)
        f.write("\n")


def fetch_assets(slug):
    """下载插画到 assets/，按原格式保存，记录指纹。

    格式处理原则（保真优先）：
      - GIF  → 原样保存（动图重新编码会变静图）
      - PNG  → 保留 alpha 通道，超大才等比缩到 1400，仍存 PNG（转 JPEG 会把透明背景变白块）
      - JPEG → 等比缩到最长边 1400，quality 88
    已存在的文件跳过，避免二次有损编码。
    """
    import urllib.request
    from PIL import Image

    spec = extract(slug)
    out_dir = os.path.join(HERE, slug, "assets")
    os.makedirs(out_dir, exist_ok=True)
    records = []
    for item in spec["images"]:
        url = item["url"]
        asset_id = url.rstrip("/").split("/")[-1]
        ext = os.path.splitext(asset_id)[1].lower()
        if ext not in (".png", ".gif", ".jpg", ".jpeg", ".webp"):
            ext = ".png"
        stem = os.path.splitext(asset_id)[0]
        final_path = os.path.join(out_dir, stem + ext)

        if os.path.exists(final_path):
            size = None
            try:
                with Image.open(final_path) as im:
                    size = list(im.size)
            except Exception:
                pass
            records.append({"url": url, "id": stem,
                            "file": "assets/" + os.path.basename(final_path),
                            "sha256": sha256_file(final_path),
                            "bytes": os.path.getsize(final_path), "size": size,
                            "count": item["count"], "where": item["where"]})
            print("  %s 已存在，跳过" % stem)
            continue

        raw_path = os.path.join(out_dir, stem + ".raw")
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=60) as r, open(raw_path, "wb") as f:
                f.write(r.read())
        except Exception as e:
            print("  下载失败 %s: %s" % (stem, e))
            continue

        size = None
        keep_raw = False
        try:
            with Image.open(raw_path) as im:
                fmt = (im.format or "").upper()
                if fmt == "GIF":
                    # 动图/透明 GIF 原样保留（必须等句柄关闭后再移动，Windows 上打开的文件不能 replace）
                    size = list(im.size)
                    keep_raw = True
                elif fmt == "PNG":
                    im2 = im.convert("RGBA")
                    im2.thumbnail((1400, 1400), Image.LANCZOS)
                    im2.save(final_path, "PNG", optimize=True)
                    size = list(im2.size)
                    os.remove(raw_path)
                else:
                    im2 = im.convert("RGB")
                    im2.thumbnail((1400, 1400), Image.LANCZOS)
                    im2.save(final_path, "JPEG", quality=88, optimize=True)
                    size = list(im2.size)
                    os.remove(raw_path)
        except Exception:
            keep_raw = True
        if keep_raw and os.path.exists(raw_path):
            os.replace(raw_path, final_path)
            if size is None:
                try:
                    with Image.open(final_path) as im:
                        size = list(im.size)
                except Exception:
                    pass

        records.append({"url": url, "id": stem,
                        "file": "assets/" + os.path.basename(final_path),
                        "sha256": sha256_file(final_path),
                        "bytes": os.path.getsize(final_path), "size": size,
                        "count": item["count"], "where": item["where"]})
        print("  %s → %s (%d 字节%s)" % (stem, os.path.basename(final_path),
                                        os.path.getsize(final_path),
                                        " %dx%d" % tuple(size) if size else ""))

    with open(os.path.join(out_dir, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump({"template": slug, "count": len(records), "assets": records},
                  f, ensure_ascii=False, indent=2)
        f.write("\n")
    return records


def main():
    ap = argparse.ArgumentParser(description="模板抽取 / 校验 / 素材下载")
    ap.add_argument("--verify", action="store_true", help="只校验不写文件")
    ap.add_argument("--fetch-assets", action="store_true", help="下载插画到 assets/（需联网）")
    ap.add_argument("--wechat-report", action="store_true", help="输出公众号兼容性报告")
    ap.add_argument("--only", default="", help="只处理某个 slug")
    args = ap.parse_args()

    slugs = [args.only] if args.only else list(TEMPLATES)
    for slug in slugs:
        if slug not in TEMPLATES:
            raise SystemExit("未知模板: %s（可选: %s）" % (slug, ", ".join(TEMPLATES)))

    if args.fetch_assets:
        for slug in slugs:
            print("[%s] 下载插画" % slug)
            fetch_assets(slug)
        print('{"ok": true, "action": "fetch-assets"}')
        return

    specs = []
    for slug in slugs:
        spec = extract(slug)
        specs.append(spec)
        if not args.verify:
            with open(os.path.join(HERE, slug, "theme.json"), "w", encoding="utf-8") as f:
                json.dump(spec, f, ensure_ascii=False, indent=2)
                f.write("\n")

    if args.wechat_report:
        for s in specs:
            print("\n[%s] %s" % (s["slug"], s["name"]))
            for issue in s["wechat_issues"]:
                print("  ⚠ " + issue)
        print()

    checks = []
    for slug in slugs:
        checks.extend(verify(extract(slug)))
    failed = [c for c in checks if not c["pass"]]
    for c in checks:
        if not c["pass"]:
            print("FAIL [%s] %s  %s" % (c["template"], c["check"], c["detail"]))

    if not args.verify and not args.only:
        write_registry(specs)

    print(json.dumps({"ok": not failed, "templates": len(slugs), "checks": len(checks),
                      "failed": len(failed)}, ensure_ascii=False))
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
