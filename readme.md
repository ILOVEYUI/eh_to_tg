# E-Hentai / ExHentai Telegram Bot

该项目实现了一个 Telegram 机器人，当用户向机器人发送 E-Hentai 或 ExHentai 画廊链接时，机器人会下载整套漫画页面并上传到 Telegraph，最后把生成的 Telegraph 页面地址发送给用户。

## 功能特性

* 识别消息中的 E-Hentai / ExHentai 画廊链接（支持 `/g/` 和 `/s/` 形式）。
* 遵循画廊原有的页面顺序下载图片。
* 下载过程中在请求之间随机延迟，降低被识别为爬虫的风险。
* 自动将图片上传至 Telegraph 并生成带有页码说明的图文页面。

## 环境准备

1. 安装依赖：

   ```bash
   pip install -r requirements.txt
   ```

2. 创建 Telegram 机器人并获取 `TELEGRAM_BOT_TOKEN`。

3. 在 Telegraph 上创建 access token，可通过官方接口 [`createAccount`](https://telegra.ph/api#createAccount) 获取，并设置环境变量 `TELEGRAPH_ACCESS_TOKEN`。

可选环境变量：

* `TELEGRAPH_AUTHOR_NAME` – Telegraph 页面显示的作者名称。
* `TELEGRAPH_AUTHOR_URL` – Telegraph 页面作者链接。

## 运行

```bash
export TELEGRAM_BOT_TOKEN="<your-telegram-token>"
export TELEGRAPH_ACCESS_TOKEN="<your-telegraph-token>"

python bot.py
```

部署后向机器人发送任意 E-Hentai / ExHentai 链接即可收到生成的 Telegraph 页面地址。
