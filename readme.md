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

2. 复制配置文件模板并填写你的凭据：

   ```bash
   cp config.example.json config.json
   ```

   * `telegram_bot_token`：Telegram 机器人 token。
   * `telegraph.access_token`：Telegraph access token，可通过官方接口 [`createAccount`](https://telegra.ph/api#createAccount) 获取。
   * `telegraph.author_name` / `telegraph.author_url`：可选的作者信息。
   * `ehentai_cookies`：访问 E-Hentai/ExHentai 所需的 cookie（如 `ipb_member_id`、`ipb_pass_hash`、`igneous`、`sk` 等）。

   如需放置在其他目录，可设置环境变量 `BOT_CONFIG_PATH` 指向配置文件路径。

## 运行

```bash
python bot.py
```

部署后向机器人发送任意 E-Hentai / ExHentai 链接即可收到生成的 Telegraph 页面地址。
