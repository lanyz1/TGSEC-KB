### 24.1 DRM保护技术全景

| 保护类型 | 技术 | 逆向难度 | 常见应用 |
|----------|------|----------|----------|
| 许可证文件 | RSA/ECDSA 签名验证 | 高(需私钥) | 商业软件、JetBrains 系列 |
| 硬件指纹 | CPU ID + MAC + 硬盘序列号 → 机器码绑定 | 中 | 单机软件、专业 CAD |
| 在线激活 | 请求服务器验证,返回激活令牌 | 高(需模拟服务器) | Adobe、Windows、游戏 |
| USB Dongle | 硬件加密狗(Feitian、SafeNet),代码与 Dongle 交互 | 高(需硬件) | 工业软件、财务软件 |
| 代码虚拟化 | VMP/Themida 保护验证逻辑 | 极高 | 游戏、专业软件 |
| White-box crypto | AES 密钥嵌入代码,无法直接提取 | 极高 | DRM、流媒体保护 |

### 24.2 许可证验证逆向方法论

通用方法论分三步:
1. **定位验证函数**:通过字符串引用(搜索 "License invalid"、"Trial expired"、"Register" 等)、API 调用模式(`RegQueryValue`、`CreateFile` 读许可证文件、`CryptVerifySignature`)、交叉引用定位验证入口。IDA 中可结合 F5 伪代码快速理解逻辑。
2. **分析验证逻辑**:判断比较方式(明文比较、哈希比较、签名验证)、密钥来源(硬编码、文件、服务器)、是否在线请求。签名验证类需关注公钥位置与签名算法(RSA-PKCS#1、ECDSA);硬件指纹类需追踪机器码生成函数。
3. **选择攻击策略**:
   - **Patch**:修改验证函数返回值(jump patch 或返回值 patch),最简单但易被完整性校验检测。
   - **Keygen**:还原密钥/序列号生成算法,编写注册机,最彻底但难度最高(需完全逆向算法)。
   - **Hook**:运行时 Hook 验证函数返回 true,不需修改磁盘文件,适合带完整性校验的目标。
   - **服务器模拟**:针对在线激活,搭建假激活服务器返回有效响应。

### 24.3 Keygen编写实战

以一个典型许可证验证为例,逆向分析发现算法后编写注册机。

```python
# 典型许可证验证: name → serial 验证
# 逆向分析发现算法:
# 1. name转换为ASCII
# 2. 每个字符乘以位置(i+1)
# 3. 求和后异或固定magic: 0xDEADBEEF
# 4. 转为十六进制字符串

def generate_serial(name):
    """根据逆向分析结果编写注册机"""
    ascii_values = [ord(c) for c in name]
    total = sum(v * (i + 1) for i, v in enumerate(ascii_values))
    serial = total ^ 0xDEADBEEF
    return f"{serial:08X}"

# 验证: generate_serial("admin") → "A1B2C3D4"
```

Keygen 编写要点:必须完整还原算法的每一步(包括字节序、大小端、有符号/无符号),一个细节错误就会导致生成的序列号无效。逆向时常通过动态调试(在比较函数处下断点)观察实际计算中间值,与自己的实现逐字节比对。对于涉及自定义哈希或加密的算法,建议用 Unicorn 模拟执行原始函数验证注册机正确性。

### 24.4 Patch验证函数

Patch 是最直接的绕过方式,核心是定位关键跳转并修改。

```assembly
; 原始验证函数:
; mov eax, [ebp+8]     ; 加载验证结果
; test eax, eax
; jz  fail             ; 如果验证失败则跳转
; ... 成功路径

; Patch方案1: NOP掉条件跳转
; jz fail → nop nop (90 90)
; 6字节: 0F 84 xx xx xx xx → 90 90 90 90 90 90

; Patch方案2: 修改返回值
; mov eax, [ebp+8]
; test eax, eax
; jz fail
; → 改为:
; mov eax, 1           ; 直接返回成功
; ret
; B8 01 00 00 00 C3

; Patch方案3: 入口直接返回true
; push ebp; mov ebp, esp
; → 改为:
; mov eax, 1; ret
; B8 01 00 00 00 C3
```

搜索关键跳转技巧:x64dbg 中用"搜索 → 条件跳转"列出所有 `jz/jnz/jne` 指令;跟踪验证函数时关注比较指令后的条件跳转。IDA 中 F5 查看伪代码,定位 `if (!check_license()) return false;` 这类关键判断,反向定位到汇编跳转。Patch 后需注意完整性校验(CRC32、数字签名),许多软件会校验自身代码段哈希,此时需同时 patch 校验函数或改用 Hook 方案。

### 24.5 硬件指纹绕过

硬件指纹通过组合 CPU ID、MAC 地址、硬盘序列号、卷序列号、主板序列号生成机器码,绑定许可证。绕过思路是分析指纹生成函数,Hook 相关 API 返回伪造值。

- **分析指纹生成**:Hook `GetVolumeInformation`(卷序列号)、`GetAdaptersInfo`(MAC)、`DeviceIoControl`(硬盘序列号,IOCTL `IOCTL_STORAGE_QUERY_PROPERTY`)、`__cpuid`(CPU ID)。
- **模拟硬件指纹**:拦截 API 返回伪造值。

```javascript
// Frida Hook硬件指纹API
Interceptor.attach(Module.getExportByName('kernel32.dll', 'GetVolumeInformationA'), {
    onLeave: function(retval) {
        // 伪造卷序列号
        var serialPtr = this.context.esp.add(0x14); // 参数位置
        serialPtr.writeU32(0x12345678); // 伪造的序列号
    }
});
```

- **虚拟机指纹**:修改 VM BIOS 序列号(VMware `.vmx` 文件 `serial` 字段)、MAC 地址(`ethernet0.address`)。
- **2026 TPM 2.0 远程证明绕过**:Windows 11 强制 TPM 2.0,部分软件通过 TPM 远程证明绑定设备。绕过方式是使用 vTPM(虚拟 TPM)模拟,或在 hypervisor 层拦截 TPM 命令返回伪造的 PCR 值与签名。

### 24.6 在线激活服务器模拟

在线激活类保护需抓包分析激活协议,搭建假服务器返回有效响应。

```python
# Flask模拟激活服务器
from flask import Flask, request, jsonify
app = Flask(__name__)

@app.route('/activate', methods=['POST'])
def activate():
    machine_id = request.json.get('machine_id')
    # 返回有效激活响应(逆向分析获得的格式)
    return jsonify({
        'status': 'success',
        'license_key': 'VALID-KEY-' + machine_id[:8],
        'expires': '2099-12-31',
        'signature': '...'  # 可能需要提取的签名
    })

# 使用: 修改hosts文件将激活服务器指向本地
# 127.0.0.1 activate.vendor.com
```

实施步骤:抓包(Burp/mitmproxy)分析激活请求与响应格式 → 用 Flask/Node 搭建模拟服务器 → 修改 `hosts` 文件将激活域名指向本地 → 若响应含签名则需逆向签名验证逻辑,可能需提取客户端公钥对应的伪造私钥(若签名验证在客户端,且公钥可替换则更简单)。SSL Pinning 绕过:若激活使用 HTTPS 且客户端校验证书,需用 Frida Hook `SecTrustEvaluate`/`SSLHandshake` 或替换客户端内置 CA 证书。2026 年云激活服务多采用 OAuth/JWT token,逆向时需分析 token 签名算法(JWT 的 HS256/RS256),伪造签名需获取共享密钥或私钥。

### 24.7 USB Dongle模拟

USB Dongle(加密狗)通过硬件存储密钥,软件运行时与 Dongle 交互验证。逆向策略:
- **提取 Dongle 固件**:用逻辑分析仪(如 Saleae)抓取 USB 通信,记录请求-响应对;或用 USBPcap 在软件运行时抓包,分析 Dongle 协议。
- **软件模拟 Dongle**:编写虚拟 USB 设备驱动(Windows 用 WinUSB/libusb,或基于 usbip 框架),在驱动层响应软件的 Dongle 请求,返回抓取的合法响应。
- **工具**:USBPcap 抓包分析、`qemu` USB passthrough 将物理 Dongle 透传到虚拟机、`usbip` 跨网络共享 Dongle。
- **2026 趋势**:USB Dongle + Cloud 双重验证,本地 Dongle 校验通过后还需云端二次验证;逆向需同时模拟 Dongle 响应与云端请求,难度提升。部分厂商改用 SDKey/TF Card 形态的智能卡 Dongle,协议更复杂。



---
📖 本切片 1/2 结束。 续篇: `skill_view(name="reverse-engineering", file_path="references/chapter-24-drm-keygen-patch-02.md")`