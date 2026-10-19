# 这是一篇示例文章

> 用它跑通「Markdown → 排版 HTML → 草稿箱」的完整链路。内容随意替换。

## 为什么要有示例

公众号排版有三类问题最容易翻车，示例里都留了位置让你验证：

1. **表格**：手机端最容易塌陷的组件
2. **图片**：外链图会被剥，必须走素材库
3. **视频**：四条嵌入路径里只有一条能活

### 一个表格

| 组件 | 风险 | 本项目处理方式 |
|---|---|---|
| 表格 | 样式在手机端塌陷 | 主题 CSS 深选择器对位（`#nice table tr th`） |
| 图片 | 外链被剥 / 裂图 | 走素材库 + aHash 配对修复 |
| 视频 | 标签被清洗 | `--video wxv_XXX` 注入原生播放器 iframe |
| SVG | 动画被过滤 | 双 g 层 + `animate begin="click"` |

### 一段代码

```bash
python scripts/wx_publish.py publish article.html --title "标题" --digest "摘要"
```

### 一个列表

- 草稿箱全套命令
- 自动封面
- 视频嵌入
- SVG 交互卡

## 怎么用这篇

```bash
# 1. 转成微信兼容 HTML（需先 npm i -g md2wechat）
md2wechat -i examples/sample-article.md -o article.html --theme orangeheart

# 2. 进草稿箱（需要凭证）
python scripts/wx_publish.py publish article.html \
  --title "这是一篇示例文章" --digest "用它跑通完整链路"

# 3. 真连验证：拉回来检查有没有乱码
python scripts/wx_publish.py draft-get <media_id> --check
```

## 落款

示例内容到此结束。替换成你自己的正文即可。
