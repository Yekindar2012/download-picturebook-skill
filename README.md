# download-picturebook

Kimi Work 技能（skill）：搜索在线翻页绘本（fliphtml5/anyflip 等），对比多个上传版本选出最优（页数全、分辨率高、含封面封底），走本机代理直连下载全部页面原图，合成为全画质 PDF 并上传到 Google Drive。

## 触发词

下载绘本、找绘本、绘本存到 Google Drive/云盘、绘本转存、搜一本绘本/图画书并下载。适用于《妈妈买绿豆》《大卫，不可以》这类公开托管的翻页电子书。

## 目录结构

```
SKILL.md                      # 技能定义与完整流程文档
scripts/fetch_pages.sh        # 经 kimi-webbridge 浏览器抓图（回退方案）
scripts/fetch_pages_direct.sh # 本机代理直连逐页下载（首选方案）
scripts/build_pdf.py          # webp 页面图合成全画质 PDF（reportlab）
```

## 免责声明

绘本版权归原作者所有，归原出版方（如信谊/明天出版社等）所有，公开上传者多为幼儿园/老师。本工具下载的电子版**仅供家庭内部阅读**，请勿用于任何商业用途或公开传播；如有条件请支持正版实体书。
