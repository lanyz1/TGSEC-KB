#!/usr/bin/env bash
# 长安COD/XunRuiCMS 系站点端到端下单验证: CSRF -> buy -> buysuccess -> 后台确认
# 用法: 改下面 BASE/SLUG/ID 变量后 bash e2e_buy_test.sh
# 验证点: 下单 code:1 + 订单号格式 + 成功页渲染 + 后台可搜到订单
# 适用于本地重建版(PHP -S)或线上目标; 线上目标注意限速+真实落库影响
set -e
BASE="http://127.0.0.1:8080"   # 目标地址
SLUG="c7f39f8317"              # 商品页 slug(伪静态)
ID="61"                        # 商品ID
SKU="0_0"                      # SKU 组合键(组ID_选项ID)
ADMIN_USER="admin"             # 后台账号(重建版自带; 线上按目标改)
ADMIN_PASS="admin123"
BUY_NAME="端到端验证"
BUY_PHONE="0912345678"         # 台湾手机强校验 09xxxxxxxx

JAR="e2e_jar.txt"
rm -f "$JAR" e2e_pro.html e2e_buy.json e2e_success.html e2e_admin_jar.txt e2e_admin_search.html

echo "=== 1. GET 商品页(同一 jar -b -c 读写, 拿 CSRF) ==="
curl -s -b "$JAR" -c "$JAR" --max-time 15 "$BASE/$SLUG" -o e2e_pro.html
CSRF=$(grep -oE 'name="csrf_test_name"[^>]*value="[a-f0-9]{32}"' e2e_pro.html | head -1 | grep -oE '[a-f0-9]{32}')
[ -n "$CSRF" ] || { echo "❌ 未提取到 CSRF 字段"; exit 1; }
echo "csrf=$CSRF"

echo "=== 2. POST buy 下单 ==="
curl -s -b "$JAR" -c "$JAR" --max-time 15 -X POST \
  "$BASE/index.php?s=order&c=order&m=buy&mid=pro&id=$ID&sku=$SKU&num=1&huilu=1&ccode=tw" \
  --data-urlencode "csrf_test_name=$CSRF" \
  --data-urlencode "paytype=nopay" \
  --data-urlencode "data[name]=$BUY_NAME" \
  --data-urlencode "data[phone]=$BUY_PHONE" \
  --data-urlencode "data[city]=1" \
  --data-urlencode "data[address]=测试地址88号" \
  --data-urlencode "data[huobi]=NT\$" \
  --data-urlencode "data[laiyuan]=$BASE/$SLUG" \
  --data-urlencode "data[wuliufangshi]=1" \
  --data-urlencode "data[pydqyf]=0" \
  --data-urlencode "data[fingerprint]=e2e_test_001" \
  -o e2e_buy.json -w "HTTP %{http_code}\n"
head -c 400 e2e_buy.json; echo

echo "=== 3. 解析成功页 URL(必须 json.loads, 响应含 \\/ 转义) ==="
SUC_URL=$(python -c "
import json,sys
d=json.load(open('e2e_buy.json',encoding='utf-8'))
if d.get('code')!=1:
    print('BUY_FAIL', d.get('msg')); sys.exit(1)
print(d['data']['url'])
")
echo "URL=$SUC_URL"
curl -s -b "$JAR" -c "$JAR" --max-time 15 "$BASE$SUC_URL" -o e2e_success.html -w "HTTP %{http_code} size %{size_download}\n"
grep -oE 'H[0-9]{16}|貨到付款|成功' e2e_success.html | sort | uniq -c | head

echo "=== 4. 后台确认落库 ==="
rm -f e2e_admin_jar.txt
curl -s -c e2e_admin_jar.txt -o NUL --max-time 15 "$BASE/index.php?s=admin&c=index&m=index"
curl -s -b e2e_admin_jar.txt -c e2e_admin_jar.txt -o NUL --max-time 15 \
  -d "user=$ADMIN_USER&pass=$ADMIN_PASS" "$BASE/index.php?s=admin&c=index&m=login"
SN=$(grep -oE 'H[0-9]{16}' e2e_success.html | head -1)
echo "订单号 SN=$SN"
curl -s -b e2e_admin_jar.txt --max-time 15 "$BASE/index.php?s=admin&c=order&m=index&kw=$SN" -o e2e_admin_search.html -w "HTTP %{http_code} size %{size_download}\n"
if grep -q "$SN" e2e_admin_search.html; then echo "✅ 订单已在后台可见"; else echo "❌ 后台未搜到"; fi
