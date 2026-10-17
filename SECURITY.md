# 安全策略

## 凭证安全

- 本项目**不存储任何凭证**：AppID/AppSecret 仅从环境变量或本地 `config.json`（已 gitignore）读取
- 如果你曾把 AppSecret 写进代码并推送到公开仓库：立即去 [微信开发者平台](https://developers.weixin.qq.com/) **重置 AppSecret**

## 报告漏洞

发现安全问题请勿公开 Issue，发邮件至仓库所有者（见 GitHub 主页），72 小时内回复。
