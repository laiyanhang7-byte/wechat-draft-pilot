# 环境与依赖指南（含三平台验证矩阵）

## 通用依赖（三平台一致）

| 依赖 | 版本 | 必需 | 说明 |
|---|---|---|---|
| Python | ≥ 3.8（实测 3.8 / 3.11 / 3.12） | ✅ | 建议装在 venv 里 |
| requests | ≥ 2.28 | ✅ | 全部微信 API 调用 |
| Pillow | ≥ 9.1（实测 11–13） | ✅ | 自动封面生成 |
| md2wechat（npm） | 最新 | 可选 | Markdown→微信 HTML 排版环节用；已有 HTML 可跳过 |
| ffmpeg | 任意 | 可选 | 仅"视频截帧做封面"用 |

安装：

```bash
pip install -r requirements.txt
# 排版环节（可选）：
npm install -g md2wechat
```

## 三平台验证矩阵（如实标注，未验证不标 ✓）

| 平台 | 验证方式 | 编译 | 单测 | CLI | 真连发布 |
|---|---|---|---|---|---|
| **Windows 10/11** | 本机实机 | ✅ | ✅ 13/13 | ✅ | ✅ 实测（草稿箱全套，2026-10） |
| **Linux** | GitHub Actions ubuntu 实测 | ✅ | ✅ | ✅ | 未实测（无 Linux 环境的公众号沙箱） |
| **macOS** | GitHub Actions macos 实测 | ✅ | ✅ | ✅ | 未实测（同上） |

> 诚实说明：三平台的**代码层**（编译/逻辑单测/CLI）由 CI 在真实 ubuntu / windows / macos 机器上验证，见 [.github/workflows/ci.yml](../.github/workflows/ci.yml)；**真连发布**只在 Windows 实机验证过。微信 API 是纯 HTTPS 调用，理论上无平台差异，但如果你在 macOS/Linux 上真连成功（或失败），欢迎 PR 更新这张表。

## 各平台注意事项

### Windows

- 控制台跑 Python 建议 `-X utf8`（`python -X utf8 scripts/wx_publish.py ...`），避免 GBK 控制台乱码
- 自动封面字体：默认用微软雅黑（`C:\Windows\Fonts\msyhbd.ttc`），无需配置
- IP 白名单：公众号后台若配置了 IP 白名单，家宽动态 IP 变动会报 `40164`

### Linux

- 中文字体：自动封面需要中文 TTF/OTF，没有时会报字体错误。装一个即可：
  ```bash
  # Debian/Ubuntu
  sudo apt install fonts-wqy-microhei fonts-noto-cjk
  # CentOS/RHEL
  sudo yum install wqy-microhei-fonts
  ```
  或在 `config.json` 里直接指定 `"font_path": "/usr/share/fonts/...ttc"`
- 其余无平台差异

### macOS

- 自动封面字体：默认找苹方（`/System/Library/Fonts/PingFang.ttc`）或冬青黑体，系统自带，无需配置
- clone 路径含中文没关系，但**不要把 tesseract 等第三方 OCR 工具装进中文路径**（与本仓库无关，但配套使用时容易踩）
- 其余无平台差异

## 配置文件（可选，凭证推荐走环境变量）

```bash
export WECHAT_APP_ID=wx你的AppID
export WECHAT_APP_SECRET=你的AppSecret
```

或 `config.json`（模板见 [config.example.json](../config.example.json)，已被 .gitignore 忽略）。
