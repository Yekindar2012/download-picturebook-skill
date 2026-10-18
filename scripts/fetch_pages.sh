#!/bin/bash
# 经 kimi-webbridge 抓取 fliphtml5 当前标签页的绘本页面图
# 用法: fetch_pages.sh <起始页> <结束页> <输出目录> [session名]
# 前提: webbridge 守护进程已启动，且当前 session 的标签页停在目标绘本页面
set -u
START=${1:?起始页}
END=${2:?结束页}
OUT=${3:?输出目录}
SESSION=${4:-picturebook}
mkdir -p "$OUT"
for n in $(seq "$START" "$END"); do
  curl -s -X POST http://127.0.0.1:10086/command -H 'Content-Type: application/json' \
    -d "{\"action\":\"evaluate\",\"args\":{\"code\":\"(async()=>{const r=await fetch('files/large/$n.webp');if(!r.ok)return JSON.stringify({status:r.status});const b=await r.blob();const buf=await b.arrayBuffer();let bin='';const bytes=new Uint8Array(buf);for(let i=0;i<bytes.length;i+=32768){bin+=String.fromCharCode.apply(null,bytes.subarray(i,i+32768));}return JSON.stringify({status:200,b64:btoa(bin)});})()\"},\"session\":\"$SESSION\"}" \
    -o "/tmp/wb-fetch-$n.json"
  python3 - "$n" "$OUT" <<'EOF'
import json, base64, sys
n, out = sys.argv[1], sys.argv[2]
d = json.load(open(f"/tmp/wb-fetch-{n}.json"))
v = json.loads(d["data"]["value"])
if v.get("status") != 200:
    print(f"page {n} FAILED {v}"); sys.exit(1)
raw = base64.b64decode(v["b64"])
open(f"{out}/page{n}.webp", "wb").write(raw)
print(f"page {n} ok {len(raw)}")
EOF
  rc=$?
  rm -f "/tmp/wb-fetch-$n.json"
  [ $rc -ne 0 ] && exit $rc
done
