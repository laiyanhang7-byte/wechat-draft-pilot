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
check("模板数量为 10（3 网页级 + 7 内联）", len(slugs) == 10, str(len(slugs)))
check("网页级模板 3 套",
      sum(1 for s in slugs if extract.TEMPLATES[s][2] == "css-var") == 3)
check("内联模板 7 套",
      sum(1 for s in slugs if extract.TEMPLATES[s][2] == "inline") == 7)
for slug in slugs:
    base = os.path.join(TPL_DIR, slug)
    check("[%s] template.html 存在" % slug, os.path.exists(os.path.join(base, "template.html")))
    check("[%s] theme.json 存在" % slug, os.path.exists(os.path.join(base, "theme.json")))

reg_path = os.path.join(TPL_DIR, "registry.json")
check("registry.json 存在", os.path.exists(reg_path))
if os.path.exists(reg_path):
    with open(reg_path, encoding="utf-8") as f:
        reg = json.load(f)
    check("registry 记录了 10 套模板", reg.get("count") == 10, str(reg.get("count")))
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
    check("[%s] 配色变量非空" % slug, len(spec["palette"]) >= 6, str(len(spec["palette"])))
    check("[%s] 字号层级已抽取" % slug, len(spec["type_scale"]) >= 4, str(len(spec["type_scale"])))
    if spec["kind"] == "css-var":
        check("[%s] 字体栈非空" % slug, len(spec["fonts"]) >= 2, str(list(spec["fonts"])))
        check("[%s] 结构类已抽取" % slug, len(spec["structure"]) >= 6, str(len(spec["structure"])))
        check("[%s] 标注了公众号兼容问题" % slug, len(spec["wechat_issues"]) >= 4,
              str(len(spec["wechat_issues"])))
    else:
        # 内联族：字体未指定属正常，但必须写明"非缺失"
        if not spec["fonts"]:
            check("[%s] 未指定字体时已注明原因" % slug, bool(spec.get("font_note")),
                  spec.get("font_note", ""))
        check("[%s] 已标注公众号兼容问题" % slug, len(spec["wechat_issues"]) >= 1,
              str(len(spec["wechat_issues"])))
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
            check("[%s] 插画 %s 非空" % (slug, aid), os.path.getsize(path) > 50,
                  "%d 字节" % os.path.getsize(path))

check("插画唯一数 79（11 + 68）", total_unique == 79, str(total_unique))
check("插画出现次数 146", total_images == 146, str(total_images))
for slug, expect in (("cream-magazine", 4), ("dopamine-pop", 12), ("forest-natural", 12),
                     ("chuli-fenfa", 21), ("rigorous-summary", 23), ("year-end-summary", 11)):
    check("[%s] 插画出现 %d 次" % (slug, expect), per_tpl.get(slug) == expect,
          str(per_tpl.get(slug)))

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

# ---------- 6. 公众号兼容性：内联族只剩「外链图」一个问题 ----------
for slug in slugs:
    with open(os.path.join(TPL_DIR, slug, "theme.json"), encoding="utf-8") as f:
        saved = json.load(f)
    if saved["kind"] == "inline":
        check("[%s] 内联族无 <style>/var()/@media 问题" % slug,
              not any(("<style>" in i or "var(--" in i or "@media" in i)
                      for i in saved["wechat_issues"]),
              str(saved["wechat_issues"]))
        check("[%s] 内联族已标出外链图问题" % slug,
              any("外链图片" in i for i in saved["wechat_issues"]),
              str(saved["wechat_issues"]))

failed = [c for c in checks if not c["pass"]]
for c in checks:
    if not c["pass"]:
        print("FAIL", c["name"], c["detail"])
print(json.dumps({"ok": not failed, "total": len(checks), "failed": len(failed),
                  "templates": len(slugs), "images": total_images}, ensure_ascii=False))
sys.exit(0 if not failed else 1)
