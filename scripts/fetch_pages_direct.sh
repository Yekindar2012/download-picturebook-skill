#!/bin/bash
# 直连下载 fliphtml5 绘本页面图（走本机代理，无需浏览器）
# 用法: fetch_pages_direct.sh <书本页URL> <起始页> <结束页> <输出目录> [代理地址]
#   书本页URL: 如 https://online.fliphtml5.com/xdzds/jopz/ （取到含末尾斜杠的书页地址）
#   代理地址:  如 http://127.0.0.1:7897；缺省时自动探测常见本地代理端口
set -u
BASE=${1:?书本页URL}
START=${2:?起始页}
END=${3:?结束页}
OUT=${4:?输出目录}
PROXY=${5:-}

if [ -z "$PROXY" ]; then
  for p in 7897 7890 1087 8888 1080 8080; do
    if curl -s -x "http://127.0.0.1:$p" -m 5 -o /dev/null "https://online.fliphtml5.com/" 2>/dev/null; then
      PROXY="http://127.0.0.1:$p"; break
    fi
  done
fi
[ -z "$PROXY" ] && { echo "no working local proxy found; pass proxy explicitly or use fetch_pages.sh (browser)"; exit 1; }
echo "using proxy $PROXY"

# 规范 base：去掉 # 锚点和末尾斜杠（否则拼出双斜杠路径会 404）
BASE=$(echo "$BASE" | sed 's/#.*//; s:/$::' )

UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
mkdir -p "$OUT"
for n in $(seq "$START" "$END"); do
  code=$(curl -sL -x "$PROXY" -A "$UA" -m 30 \
    -o "$OUT/page$n.webp" -w "%{http_code}" "$BASE/files/large/$n.webp")
  # 000 等瞬时错误重试一次
  if [ "$code" = "000" ]; then
    sleep 1
    code=$(curl -sL -x "$PROXY" -A "$UA" -m 30 \
      -o "$OUT/page$n.webp" -w "%{http_code}" "$BASE/files/large/$n.webp")
  fi
  if [ "$code" != "200" ]; then
    rm -f "$OUT/page$n.webp"
    echo "page $n HTTP $code (若为 404 说明已到最后一页)"
    [ "$code" = "404" ] && break
    exit 1
  fi
  echo "page $n ok $(stat -f%z "$OUT/page$n.webp")"
done
