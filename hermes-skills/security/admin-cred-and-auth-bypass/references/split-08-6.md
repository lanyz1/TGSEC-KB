## 6. 工具

### `scripts/admin_cred_hunter.py` —— 凭据来源清道夫(纯 stdlib 零依赖)
```bash
python3 scripts/admin_cred_hunter.py -u https://T/admin -o D:/渗透/T_admin
python3 scripts/admin_cred_hunter.py -u https://T/admin -o D:/渗透/T_admin \
        --probe-login --login https://T/prod-api/login     # 小样本默认口令(带锁定保护)
python3 scripts/admin_cred_hunter.py -f urls.txt -o D:/渗透/batch --threads 6
```
做什么: ①基线法剔 catch-all ②后台指纹+登录端点定位 ③154 条凭据来源路径分 tier 扫
④前端 JS 挖密(口令/密钥/云AK/JWT/内网地址/隐藏接口/注释)⑤小样本默认口令差分探测 + 锁定保护。
输出 `report.md`(按价值分层)+ `findings.json` + `js/`。

### `scripts/vuln_admin_site.py` —— 本机回归靶场
```bash
python3 scripts/vuln_admin_site.py 8899          # /admin  默认口令 admin/admin888 可进
python3 scripts/vuln_admin_site.py 8899 spa      # 未知路径一律 200 兜底(测假阳性)
# /admin2 路径带 5 次失败锁定,用于验证锁定保护
```
改动工具后**必须**跑这三个场景回归,别只跑语法检查。

---

