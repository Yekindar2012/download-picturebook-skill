---
name: download-picturebook
description: 搜索在线翻页绘本（fliphtml5/anyflip 等），对比多个上传版本选出最优（页数全、分辨率高、含封面封底），走本机代理直连下载全部页面原图，合成为 PDF 并上传到 Google Drive 的 Kimi_download 文件夹（云端，本地不保留副本）。触发词：下载绘本、找绘本、绘本存到 Google Drive/云盘、绘本转存、搜一本绘本/图画书并下载。适用于《妈妈买绿豆》《大卫，不可以》这类公开托管的翻页电子书。
---

# 下载绘本到 Google Drive

## 流程总览

1. **搜索候选版本**：用 WebSearch 搜「书名 fliphtml5」（也可补 anyflip）。同一本书通常有多个用户上传版本。
2. **逐个检查版本质量**：对每个候选链接，用 `curl -x <本机代理>` 直连页面（见 scripts/fetch_pages_direct.sh 的代理自动探测），用 grep 抽 `files/large/N.webp` 确认可访问，然后循环 GET 探测 `files/large/1..80.webp` 的 404 边界得到总页数，并取第 1 页 `file` 命令确认分辨率：

```bash
BASE="https://online.fliphtml5.com/<user>/<book>"   # 不带末尾斜杠
curl -sL -x "$PROXY" -A "$UA" -o p1.webp "$BASE/files/large/1.webp" && file p1.webp
```

3. **选最优版本**，优先级：页数完整（含封面/封底）> 单页分辨率高 > 单页体积大（画质指标）。
4. **逐页下载**：`bash scripts/fetch_pages_direct.sh "<书本页URL>" 1 <总页数> <输出目录>`。脚本自动探测本机代理端口（7897/7890/1087/8888/1080/8080），逐页 GET `files/large/N.webp` 存为 `pageN.webp`，遇 404 自动停止。
5. **合成 PDF**：`python3 scripts/build_pdf.py <图片目录> <输出.pdf>`。保留原图分辨率，JPEG q92 嵌入，全画质不降采样。绘本 PDF 通常 15~30 MB。
6. **上传 Google Drive** 到 Kimi_download 文件夹（ID `<你的 Kimi_download 文件夹 ID（在 Drive 中创建后填入，勿提交到公开仓库）>`，若在用户的 Drive 中找不到该文件夹则创建，用 google-drive MCP 的 `create_file` 建 folder），上传方式按体积二选一：
   - **PDF < 7 MB**：用 google-drive MCP `create_file`，`base64Content` 传内容、`contentMimeType="application/pdf"`、`disableConversionToGoogleType=true`、parentId 为文件夹 ID。注意 agent-gw 网关请求体限制约 14 MB（base64 后），所以二进制约 7 MB 是上限。
   - **PDF ≥ 7 MB（常见）**：走浏览器网页上传——kimi-webbridge `navigate` 打开 `https://drive.google.com/drive/folders/<文件夹ID>`，snapshot 点「新建 → 文件上传」，再操作文件对话框。**webbridge 的 `upload` 和 CDP `DOM.setFileInputFiles` 会被扩展权限拦截**（缺「允许访问文件网址」），改用 **kimi-cu 操作 macOS 原生打开对话框**：对话框弹出后用 Cmd+Shift+G 输入 PDF 绝对路径、回车。上传完成后轮询网页文件列表确认文件名出现且进度条消失，再用 MCP `get_file_metadata` 核对 fileSize 与本地一致。
7. **确认上传成功后清理本地**：删除工作区 PDF 和 pages_* 图片目录。上传未确认前绝不删本地文件。

## 代理与回退

- 直连被 CloudFront geo-block（403 "block access from your country"）是因为沙箱出口不走代理。**首选走本机代理**：探测 `127.0.0.1` 常见端口（Clash Verge 默认 7897、Clash 7890、Surge 1087…），用 `curl -x http://127.0.0.1:<port>` 验证后直连，速度快且无需浏览器。探测目标建议直接用 `https://online.fliphtml5.com/`（Google 可能被单独墙时 fliphtml5 仍通）。
- 只有当本机没有可用代理时，才回退到 kimi-webbridge 浏览器方案抓图：守护进程 `http://127.0.0.1:10086/command`（未启动先跑 `~/.kimi-webbridge/bin/kimi-webbridge start`），`navigate` 打开书本页后用 `scripts/fetch_pages.sh <起> <止> <目录> <session>` 经 evaluate + base64 抓图。注意 fetch 的是**当前标签页**，切页后先核对 `document.title`。

## 关键坑位

- **URL 双斜杠 404**：拼路径时 base 必须去掉末尾斜杠，否则 `jopz//files/...` 返回 404。fetch_pages_direct.sh 已处理。
- **图片路径**：新版 fliphtml5 是 `files/large/N.webp`（旧教程里的 .jpg 已 404），`javascript/config.js` 是混淆的，别去解析它，直接探测 URL 规律即可。
- **分页器不可信**：页数以递增探测 404 的循环为准，DOM 里的页码文本不可靠。探测要带重试（代理瞬时故障会返回 000）。
- **纯空白页**：个别页下载下来只有几 KB，用 PIL 检查亮度——std=0 且全 255 是源书自带的空白页，保留即可，不是损坏。
- **Pillow JPEG**：该运行环境的 Pillow 默认未注册 JPEG 保存器，`Image.SAVE` 为空，必须先 `from PIL import JpegImagePlugin` 再 save jpg（features.check('jpg') 为 True 不代表已注册）。WebP 只可读不可写。
- **体积控制**：不要为省体积降采样或 256 色量化——用户明确要画质优先。
- webbridge 所有命令带 `session` 字段；一次任务一个 session 名，标签页归入一个分组。

## 版权提示

转述给用户：电子版适合家庭内部阅读；原书为正版出版物（如信谊/明天出版社），公开上传者多为幼儿园/老师。