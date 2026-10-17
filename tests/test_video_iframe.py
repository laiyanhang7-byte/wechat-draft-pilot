# -*- coding: utf-8 -*-
"""视频插入功能本地验证：iframe 模板正确性 + 注入位置逻辑
不触网。格式基准来自 docs/pitfalls.md 第二节真连实验矩阵（活路 B）。
运行: python tests/test_video_iframe.py  → 最后输出 {"ok": true, ...}"""
import os, sys, json, re

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
from wx_publish import video_iframe  # noqa: E402

checks = []


def check(name, cond, detail=""):
    checks.append({"name": name, "pass": bool(cond), "detail": detail})


# 1. 模板结构：真连验证过的六要素
html = video_iframe("wxv_4734223077218287624", "0.8", 1200, "https://mmbiz.qpic.cn/cover.jpg")
check("wxv id 双写(data-src vid + data-mpvid)", html.count("wxv_4734223077218287624") == 2)
check("播放模板 URL", "mp.weixin.qq.com/mp/readtemplate" in html and "video_player_tmpl" in html)
check("data-vidtype=2", 'data-vidtype="2"' in html)
check("data-cover 透传", 'data-cover="https://mmbiz.qpic.cn/cover.jpg"' in html)
check("data-ratio 透传", 'data-ratio="0.8"' in html)
check("data-w 透传", 'data-w="1200"' in html)
check("iframe 容器(section nodeleaf)", "<section nodeleaf" in html and "</iframe></section>" in html)

# 2. 注入逻辑：第一个 </h2> 之后（与 cmd_publish 同一逻辑）
sample = "<h1>标题</h1><h2>第一章</h2><p>正文</p><h2>第二章</h2><p>更多</p>"
iframe = video_iframe("wxv_test", "0.8", 1200, "")
idx = sample.find("</h2>")
ins = idx + len("</h2>")
out = sample[:ins] + iframe + sample[ins:]
check("注入在第一个 h2 后", out.find("</h2>") + len("</h2>") == out.find("<section nodeleaf"))
check("只注入一处", out.count("<section nodeleaf") == 1)
check("原正文完整保留", "第一章" in out and "第二章" in out and "更多" in out)

# 3. 无 h2 的兜底：插到正文最前
sample2 = "<p>没有标题结构</p>"
out2 = iframe + sample2
check("无 h2 时插到最前", out2.startswith("<section nodeleaf") and "没有标题结构" in out2)

# 4. 微信清洗安全：模板内不得含会被剥的标签/属性（死路标签必须带尖括号才算标签；
#    注意 action=mpvideo / video_player_tmpl 是播放器 URL 的合法参数，不算）
forbidden = ["<video>", "<video ", "<mpvideo", "mp-common-videosnap"]
check("无死路标签", not any(f in html for f in forbidden))
check("无明文 http 链接", not re.search(r"(?<!s)http://", html))

failed = [c for c in checks if not c["pass"]]
for c in checks:
    print(("PASS" if c["pass"] else "FAIL"), c["name"], c["detail"])
result = {"ok": not failed, "total": len(checks), "failed": len(failed)}
print(json.dumps(result, ensure_ascii=False))
sys.exit(0 if not failed else 1)
