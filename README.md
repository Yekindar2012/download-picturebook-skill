# download-picturebook

下载公开绘本页面并合成 PDF；按用户要求上传到其 Google Drive。

当前版本采用隐私加固默认值：HTTPS 域名白名单、拒绝重定向和带凭据 URL、禁用 curl 用户配置与继承的网络环境、不使用浏览器 Cookie、私有文件权限、下载大小上限、不覆盖已有输出。

## 使用

需要 Python 3.10+、curl、Pillow、reportlab。使用可信来源提供的依赖。

```bash
umask 077
task_dir=$(mktemp -d ./picturebook.XXXXXX)
bash scripts/fetch_pages_direct.sh 'https://online.fliphtml5.com/USER/BOOK/' 1 80 "$task_dir/pages"
python3 -I scripts/build_pdf.py "$task_dir/pages" "$task_dir/book.pdf"
```

支持 online.fliphtml5.com 和 online.anyflip.com 的两段书本路径。默认不使用代理；可在下载命令最后追加无认证的本地 HTTP 代理地址。不传入密码、token 或签名链接。

浏览器回退已停用；旧的 fetch_pages.sh 会直接报错退出。云盘上传流程见 SKILL.md，只有用户要求上传时执行，不支持绕过连接器大小或权限限制。

验证：`python3 -m unittest discover -s tests -v`。

当前版本不会清除旧提交中的个人文件夹 ID，也无法保证外部代理、连接器或主机的安全。只下载有权使用的内容。
