## 附录A: 证据收集模板

```json
{
  "vulnerability": "Account Opening Security Bypass",
  "type": "KYC Bypass / Identity Verification Flaw",
  "target": "券商/银行/支付平台 开户系统",
  "attack_vector": "活体检测注入 / 身份证OCR绕过 / 合成身份",
  "steps": [
    "1. 创建虚拟摄像头设备",
    "2. 注入预录/AI生成视频",
    "3. 通过活体检测",
    "4. 提交合成身份信息",
    "5. 成功开户"
  ],
  "impact": "可绕过KYC身份验证，以虚假身份开设账户，用于洗钱、套现、薅羊毛等非法活动",
  "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:N",
  "cvss_score": 9.1,
  "remediation": [
    "1. 部署虚拟摄像头注入检测（设备指纹/PRNU/时间戳验证）",
    "2. 实施多模态交叉验证（人脸+证件+手机号+银行卡四要素）",
    "3. 引入AI生成内容检测（证件、人脸、视频）",
    "4. 增加人工审核环节（高风险开户）",
    "5. 实施行为分析（检测AI Agent模式）",
    "6. 跨平台身份信息交叉验证",
    "7. 定期更新活体检测算法对抗最新攻击"
  ]
}
```

---

