# 踩坑全集（实战验证，全部真连复测）

> 本文档来自真实公众号运营环境的实战踩坑记录，所有结论均经真连验证。欢迎补充你的踩坑案例（PR）。

## 一、草稿接口（最高频事故区）

### 1. draft/update 三大坑（比 draft/add 严）
- **必须整体 JSON body**：`{"media_id":..., "index":0, "articles":{...}}` 放 body；用 multipart files 传报 `40007 invalid media_id`。
- **必须显式 UTF-8**：`requests.post(json=...)` 默认 ensure_ascii=True，中文变 `\uXXXX` 转义，**微信 update 接口不解析该转义，原样入库=全文乱码**（实战事故：一次 1969 处）。正确写法：
  ```python
  body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
  requests.post(url, data=body, headers={"Content-Type": "application/json"})
  ```
  draft/add 同理（本仓库 scripts/wx_publish.py 已固化正确写法）。
- **字段按 UTF-8 字节限长**：title 64 字节 ≈ 21 个汉字（25 字标题 71 字节报 `45003 title size out of limit`）；author 同样紧（四个汉字 12 字节报 `45110`，两个汉字可过）。update 前先想好短标题。

### 2. update 失败会把草稿清空（隐蔽事故）
- 对一个草稿调 draft/update 时若中途报错（实测：缩略图 media_id 异常触发 `40007 invalid media_id`），**微信会先清空该草稿的 articles 再校验**——草稿变空壳，且此后对同一 media_id 的 update 持续报 40007（index 0 已无可更新文章）。
- **恢复方法**：不要恋战，直接用最终内容 `draft/add` 新建一个草稿，再 `draft/delete` 删掉空壳旧稿即可，原 media_id 无法救回。
- **预防**：update 前先把将要写入的封面缩略图（thumb_media_id）单独验一遍有效性；新封面素材建议用 JPG（PNG 实测可疑，未定论）。

### 3. 检验纪律
- 一切"应该好了"无效，必须 `draft/get` 拉回服务器侧内容逐项核对。
- 乱码检验指标：`\u` 字面残留 / `Ã` 双编码 / U+FFFD 替换符 / 连续问号（`draft-get --check` 已内置）。
- 终端显示乱码 ≠ 数据乱码：Git Bash 的 cat 对 UTF-8 按 GBK 显示是假象，以检验指标为准。
- **拉取端假乱码（已修）**：微信 API 返回 content-type 不带 charset 时，`requests` 的 `r.json()` 按 ISO-8859-1 误读，中文全变 `æ¢` 类假乱码——是显示端问题，草稿本身完好。正确写法（wx_publish.py 已固化）：`json.loads(r.content.decode("utf-8"))`，禁止裸用 `r.json()`；遇到 `--check` 报乱码先用显式解码复验再定论。

## 二、正文嵌视频（实验矩阵收官）

| 方式 | API 入库 | 前端渲染 | 结论 |
|---|---|---|---|
| `<mpvideo>`（素材库 apiv_ vid） | 保留 | ❌ 空白占位 | 死路 |
| `<mp-common-videosnap>`（视频号） | 被清洗 | - | 死路 |
| HTML5 `<video>` | 被清洗 | - | 死路 |
| **腾讯视频 iframe（v.qq.com）** | 保留 | ✅ | 全自动活路 A |
| **mp.weixin.qq.com 播放模板 iframe（wxv_ id）** | 保留 | ✅ | **全自动活路 B（首选）** |

- **根因**：API 上传视频 get_material 返回的 vid 是 `apiv_` 前缀，微信前端只认 `wxv_` 前缀。
- **wxv id 获取**：视频在后台编辑器手动插入一次 → `draft/get` 拉回 → 提取 iframe 的 `data-mpvid`（`wxv_` 开头）→ 存档复用（id 永久有效）。
- **复用模板**：`wx_publish.py` 的 `video_iframe(wxv, ratio, width, cover_enc)`；`publish --video wxv_XXX` 自动插到第一个 h2 后。
- 素材库视频上传接口本身是通的（`video-add`），只是不能直接嵌正文；素材库视频积累多了用 batchget + del_material 清理。
- 视频截帧做封面：`ffmpeg -ss 3 -i 视频.mp4 -frames:v 1 -q:v 3 输出.jpg`。

## 三、md2wechat 排版（主题）

- convert 必须显式 `--theme 名字`，`.env` 的 THEME 键对 convert 无效（CLI 默认值硬编码）。
- **选择器特异性坑**：basic.css 用深选择器（`#nice table tr th`、`#nice .multiquote-1 p`、`#nice li section`），主题 css 必须先 grep basic.css 拿真实选择器**对位写**，浅选择器（如 `#nice th`）必输（与加载顺序无关）。
- 主题规范：`#nice` 前缀、纯静态值、**禁 CSS 变量/calc/box-shadow**（微信不认；doocs/md 开源主题用了变量，移植需展开）。
- sync-* 命令无 --theme 参数：先 `convert --theme` 再 `sync-html -u <media_id>` 更新。

## 四、凭证与环境

- **凭证勿入代码库**：AppID/AppSecret 只放环境变量（`WECHAT_APP_ID` / `WECHAT_APP_SECRET`）或本地 `config.json`（已 gitignore）。AppSecret 管理入口：**微信开发者平台 developers.weixin.qq.com**（后台迁移过，旧公众平台找不到属正常）。
- **IP 白名单**：公众号后台配置了 IP 白名单时，本机公网 IP 变动会报 `40164`——查新 IP 去开发者平台重加；家宽动态 IP 建议留意这一条。
- Windows：Python 一律 `-X utf8`；禁内联 `python -c` 拼长文本（转义炸），写脚本文件；Git Bash 的 grep/find 是 rg/fd 别名，`-E` 含义不同。
- 订阅号群发限制：每天 1 次；freepublish 直接发布=群发，建议保留草稿箱人工确认。

## 五、SVG 交互

- 双 g 层 + `animate begin="click"`（遮罩 1→0、内容 0→1）、`restart="never"`、svg 带 xmlns、内联 style 控宽。
- 文本特殊引号用数字实体（`&#8220;`）。
- 视频/图片不用的花样：滑动翻页、擦除揭晓、多区域点击弹海报（壹伴/135 模板本质同款代码）。

## 六、账号权限矩阵（未认证个人订阅号实测，2026-10-12 首测 / 2026-10-17 复测一致）

**✅ 可用**：草稿箱全套（add/update/get/batchget）、素材管理（图片/视频上传+查询+删除）、菜单/自动回复配置读取（get_current_selfmenu_info / get_current_autoreply_info）、账号信息。

**❌ 48001 需微信认证（个人订阅号无法认证，硬墙）**：datacube 数据统计全家（阅读/涨粉/转发）、tags 标签、user 粉丝列表、qrcode 带参数二维码（渠道码）、shorturl、comment 评论管理（带 /cgi-bin 前缀时 48001）。

**❌ 404 接口不存在**：freepublish/* 发布（未认证订阅号 API 面直接裁掉，返回非 JSON 空响应）。

**探测注意**：tags/user/qrcode/shorturl/menu 路径必须带 `/cgi-bin` 前缀（`https://api.weixin.qq.com/cgi-bin/...`），漏了返回空响应；comment/freepublish 不带前缀但未认证号直接 404。

**IP 白名单坑**：get_token（access_token 获取）受 IP 白名单校验，家宽动态 IP 变动即报 `40164 invalid ip x.x.x.x, not in whitelist`——token 拿到后的其他调用不再查 IP。微信无白名单修改 API，只能人工去开发者平台改；根治方案=固定出口 IP（云服务器正向代理）。

## 七、自动发布红线（2026-04 新规，必读）

《微信公众平台运营规范》2026 年更新：**不得利用 AI、脚本、接口自动化方式替代真人完成内容创作、发布等流程**；处罚阶梯：限流 → 删除 → 能力限制 → 封禁。打击对象=全自动批量发布+低质 AIGC 灌水；鼓励对象=真人创作+工具辅助。

**本项目的安全设计（勿改）**：自动进草稿箱 + 人工审核 + 人工点发布。不接入 freepublish 全自动发布（个人订阅号也无权限，见上）。内容应有真实业务背景，发布前人工过目。订阅号群发每日 1 次，freepublish_submit 每次消耗 1 次、删除不返还。

## 八、正文配图通道（裂图事故复盘，已修）

- **`material/add_material` 返回的 url 不能用于正文**：那是素材库管理链接，嵌进 draft content 后手机端渲染出裂图（实战事故：整组小贴纸全部裂图）。**正文配图一律走 `media/uploadimg`**（官方"图文消息内的图片"接口，≤10MB，返回可直接嵌正文的 url），返回 http:// 时替换成 https://。
- 素材接口会重压缩图片，返回内容与上传文件字节不一致——**按 md5 配对本地文件必失败，用 aHash 感知哈希配对**（16x16 灰度均值哈希，像素内容不变）。
- 修复脚本：`scripts/fix_content_images.py`（自动抽取草稿 HTML 里的 mmbiz URL → aHash 配对本地 jpg → uploadimg 换新 → 生成 *_fix.html），配合 `wx_publish.py update` 批量更新旧草稿。
- 终验脚本模式：draft-get 拉回内容 → 抽全部图片 URL → 断言无 http://、无已知坏 URL 特征、逐 URL 实测 GET 200 且 content-type 为 image。
- **头图（content 里的 hero img）也走 uploadimg**；封面缩略图（thumb_media_id）仍走 add_material 永久素材，两者通道不同勿混。
