### 24.8 White-box密码学对抗

White-box 密码学将密钥嵌入在查找表中,即使在白盒环境(攻击者完全控制执行)下也无法直接提取密钥,常用于 DRM 与支付保护。以 White-box AES 为例,密钥被编码进 T-table 与外部编码,直接逆向查找表无法还原密钥。

攻击方法:
- **Differential Computation Analysis (DCA)**:类似硬件侧信道的 DPA,对白盒实现执行大量已知明文,记录中间值,用相关性分析恢复密钥字节,适用于未做足够混淆的白盒实现。
- **Differential Fault Analysis (DFA)**:在白盒执行中注入故障(如翻转中间状态字节),通过故障输出与正常输出的差异恢复密钥,经典攻击可在 2 组故障下恢复 AES-128 密钥。
- **BGE attack**:针对 Chow 等人提出的白盒 AES 实现的代数攻击,利用 T-table 的代数结构还原密钥,对原始 Chow 实现有效。
- **工具**:SideTrail(侧信道分析框架)、WhibOx contest winners(历届白盒密码竞赛的攻击代码)。

2026 年趋势:NIST 推进 White-box 密码学标准化(结合 PQC 后量子密码),新标准强调抗 DCA/DFA 能力;但学术界持续发现对标准化候选方案的攻击,White-box 与攻击者的博弈仍在持续。对逆向工程师而言,面对 White-box 保护的目标,DCA/DFA 仍是首选低成本攻击手段。

---



---
📖 本切片 2/2 结束。 本章节结束。