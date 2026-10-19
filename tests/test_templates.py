# -*- coding: utf-8 -*-
"""模板资产验收：字体、颜色、插画三样都不许丢。

跑法: python tests/test_templates.py  → 最后输出 {"ok": true, ...}

与 templates/extract.py --verify 的分工：
  extract.py 负责「抽取 + 对账」（模板 → theme.json）
  本文件负责「资产完整性」（theme.json → 磁盘上的插画文件是否真的在、指纹是否对得上）
两者都过，才算模板可用。
"""
import hashlib
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TPL_DIR = os.path.join(REPO, "templates")
sys.path.insert(0, TPL_DIR)

import extract  # noqa: E402

checks = []


def check(name, cond, detail=""):
    checks.append({"name": name, "pass": bool(cond), "detail": detail})


def sha256_file(path):
    """与 extract.sha256_file 一致：统一按 LF 计算，避免 CRLF 检出导致误报"""
    return extract.sha256_file(path)


slugs = list(extract.TEMPLATES)

# ---------- 1. 结构完整性 ----------
check("模板数量为 3", len(slugs) == 3, str(slugs))
for slug in slugs:
    base = os.path.join(TPL_DIR, slug)
    check("[%s] template.html 存在" % slug, os.path.exists(os.path.join(base, "template.html")))
    check("[%s] theme.json 存在" % slug, os.path.exists(os.path.join(base, "theme.json")))

reg_path = os.path.join(TPL_DIR, "registry.json")
check("registry.json 存在", os.path.exists(reg_path))
if os.path.exists(reg_path):
    with open(reg_path, encoding="utf-8") as f:
        reg = json.load(f)
    check("registry 记录了 3 套模板", reg.get("count") == 3, str(reg.get("count")))
    check("registry 的 slug 与目录一致",
          sorted(t["slug"] for t in reg["templates"]) == sorted(slugs),
          str([t["slug"] for t in reg["templates"]]))

# ---------- 2. 抽取结果与模板文件对账 ----------
all_palettes = {}
for slug in slugs:
    spec = extract.extract(slug)
    with open(os.path.join(TPL_DIR, slug, "theme.json"), encoding="utf-8") as f:
        saved = json.load(f)

    check("[%s] 指纹一致" % slug, saved["source_sha256"] == spec["source_sha256"],
          "%s vs %s" % (saved["source_sha256"][:10], spec["source_sha256"][:10]))
    check("[%s] 配色变量非空" % slug, len(spec["palette"]) >= 5, str(len(spec["palette"])))
    check("[%s] 字体栈非空" % slug, len(spec["fonts"]) >= 2, str(list(spec["fonts"])))
    check("[%s] 字号层级 ≥ 8 级" % slug, len(spec["type_scale"]) >= 8, str(len(spec["type_scale"])))
    check("[%s] 结构类已抽取" % slug, len(spec["structure"]) >= 6, str(len(spec["structure"])))
    all_palettes[slug] = set(v.lower() for v in spec["palette"].values())

# 三套风格不能是同一套配色（防复制粘贴串味）
check("三套模板配色互不相同",
      len({frozenset(v) for v in all_palettes.values()}) == len(slugs),
      str({k: len(v) for k, v in all_palettes.items()}))

# ---------- 3. 插画：文件真的在，指纹对得上 ----------
total_images = 0
total_unique = 0
per_tpl = {}
for slug in slugs:
    with open(os.path.join(TPL_DIR, slug, "theme.json"), encoding="utf-8") as f:
        saved = json.load(f)
    imgs = saved["images"]
    total_unique += len(imgs)
    total_images += sum(i["count"] for i in imgs)
    per_tpl[slug] = sum(i["count"] for i in imgs)
    check("[%s] 插画清单非空" % slug, len(imgs) >= 2, "%d 张" % len(imgs))
    for item in imgs:
        aid = item["url"].rstrip("/").split("/")[-1]
        rel = item.get("file") or ""
        path = os.path.join(TPL_DIR, slug, rel) if rel else ""
        check("[%s] 插画 %s 已落盘" % (slug, aid), bool(rel) and os.path.exists(path), path or "(未下载)")
        if rel and os.path.exists(path):
            check("[%s] 插画 %s 指纹一致" % (slug, aid), sha256_file(path) == item.get("sha256", ""),
                  "%d 字节" % os.path.getsize(path))
            check("[%s] 插画 %s 非空" % (slug, aid), os.path.getsize(path) > 5000,
                  "%d 字节" % os.path.getsize(path))

check("插画唯一数 11（3+4+4）", total_unique == 11, str(total_unique))
check("插画出现次数 28（含 deco/sticker 复用）", total_images == 28, str(total_images))
check("奶油插画出现 4 次", per_tpl.get("cream-magazine") == 4, str(per_tpl.get("cream-magazine")))
check("多巴胺插画出现 12 次", per_tpl.get("dopamine-pop") == 12, str(per_tpl.get("dopamine-pop")))
check("森系插画出现 12 次", per_tpl.get("forest-natural") == 12, str(per_tpl.get("forest-natural")))

# ---------- 4. manifest 与 theme.json 一致 ----------
for slug in slugs:
    mp = os.path.join(TPL_DIR, slug, "assets", "manifest.json")
    check("[%s] assets/manifest.json 存在" % slug, os.path.exists(mp))
    if not os.path.exists(mp):
        continue
    with open(mp, encoding="utf-8") as f:
        man = json.load(f)
    with open(os.path.join(TPL_DIR, slug, "theme.json"), encoding="utf-8") as f:
        saved = json.load(f)
    man_urls = {a["url"] for a in man["assets"]}
    tpl_urls = {i["url"] for i in saved["images"]}
    check("[%s] manifest 与 theme.json 的插画 URL 一致" % slug, man_urls == tpl_urls,
          "manifest %d / theme %d" % (len(man_urls), len(tpl_urls)))
    check("[%s] manifest 每张图都有尺寸信息" % slug,
          all(a.get("size") for a in man["assets"]),
          str([a["id"] for a in man["assets"] if not a.get("size")]))

# ---------- 5. 内联 SVG（装饰插画）不能丢 ----------
with open(os.path.join(TPL_DIR, "forest-natural", "theme.json"), encoding="utf-8") as f:
    fn = json.load(f)
check("森系保留内联枝丫装饰（twig × 2）", fn["inline_svg"].get("twig") == 2, str(fn["inline_svg"]))

# ---------- 6. 公众号兼容性已如实标注 ----------
for slug in slugs:
    with open(os.path.join(TPL_DIR, slug, "theme.json"), encoding="utf-8") as f:
        saved = json.load(f)
    check("[%s] 已标注公众号兼容问题" % slug, len(saved["wechat_issues"]) >= 4,
          str(len(saved["wechat_issues"])))

failed = [c for c in checks if not c["pass"]]
for c in checks:
    if not c["pass"]:
        print("FAIL", c["name"], c["detail"])
print(json.dumps({"ok": not failed, "total": len(checks), "failed": len(failed),
                  "templates": len(slugs), "images": total_images}, ensure_ascii=False))
sys.exit(0 if not failed else 1)
