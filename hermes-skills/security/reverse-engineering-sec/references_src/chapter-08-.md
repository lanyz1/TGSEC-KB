## 8. 硬件逆向 — 侧信道攻击与故障注入

### 8.1 功耗分析攻击

每次CPU执行指令——特别是加密操作——都会消耗微小功率。通过高灵敏度探头连接MCU电源轨并用示波器监控功耗：

**简单功耗分析(SPA)** — 直接观察功耗轨迹中的操作特征：

```python
# ChipWhisperer SPA分析
import chipwhisperer as cw

scope = cw.scope()
target = cw.target(scope)

# 捕获功耗轨迹
scope.adc.samples = 24000
trace = cw.capture_trace(scope, target, plaintext, key)

# 分析功耗轨迹识别AES轮操作
import numpy as np
import matplotlib.pyplot as plt

plt.plot(trace.wave)
plt.title('SPA: AES Power Trace')
plt.xlabel('Sample')
plt.ylabel('Power')
plt.show()
# 可观察到10轮AES的功耗峰值模式
```

**差分功耗分析(DPA)** — 对数千条功耗轨迹的统计分析直接从硅片提取加密密钥：

```python
# DPA攻击AES-128
# 1. 捕获N条功耗轨迹(不同明文,相同密钥)
# 2. 对每个密钥假设,计算中间值(如S-box输出)
# 3. 根据中间值某bit将轨迹分为两组
# 4. 计算两组功耗均值之差
# 5. 正确密钥假设产生最大差分峰值

import numpy as np

traces = np.load('traces.npy')        # N x T 功耗矩阵
plaintexts = np.load('plaintexts.npy') # N x 16 明文数组

sbox = np.array([...])  # AES S-box

for key_byte in range(16):
    max_corr = 0
    best_key = 0
    for k in range(256):
        # 计算中间值
        intermediate = sbox[plaintexts[:, key_byte] ^ k]
        # 取LSB作为分组依据
        group0 = traces[intermediate & 1 == 0]
        group1 = traces[intermediate & 1 == 1]
        # 差分均值
        diff = np.abs(np.mean(group0, axis=0) - np.mean(group1, axis=0))
        if np.max(diff) > max_corr:
            max_corr = np.max(diff)
            best_key = k
    print(f"Key byte {key_byte}: 0x{best_key:02x} (corr={max_corr:.4f})")
```

### 8.2 故障注入 — 电压毛刺

在CPU执行关键指令时瞬间降低电压，使CPU恰好在一个时钟周期内逻辑失效：

```text
电压毛刺攻击Secure Boot绕过:
  目标: if (firmware_signature_valid == TRUE) { boot(); }
  
  1. 监控目标功耗确定安全检查时序
  2. 在签名验证指令执行时注入电压毛刺
  3. 毛刺宽度: 10-50ns (恰好使比较器跳过)
  4. CPU跳过安全检查 → 执行未签名固件

  ChipWhisperer配置:
    scope.glitch.clk_src = 'target'
    scope.glitch.offset = 31234   # 精确时钟偏移
    scope.glitch.width = 15        # 毛刺宽度(个时钟周期)
    scope.glitch.repeat = 1
    scope.glitch.trigger_src = 'manual'
```

### 8.3 硬件逆向工具全景

| 工具 | 类型 | 功能 |
|---|---|---|
| ChipWhisperer | 开源 | 侧信道分析+故障注入平台 |
| lascar (Ledger Donjon) | 开源 | 侧信道分析库 |
| Riscure Inspector | 商用 | 专业侧信道分析 |
| JTAGulator | 开源硬件 | 发现和识别JTAG接口 |
| Glasgow Interface Explorer | 开源硬件 | 多协议硬件接口 |
| Saleae Logic Analyzer | 商用 | 逻辑分析(协议嗅探) |

### 8.4 防御技术(逆向工程对抗)

```c
// 常量时间内存比较 — 防止时序侧信道
uint8_t secure_memcmp_constant_time(const uint8_t *a, const uint8_t *b, size_t length) {
    uint8_t result = 0;
    for (size_t i = 0; i < length; i++) {
        result |= (a[i] ^ b[i]);
    }
    return result;  // 0=匹配, 非0=不匹配
}
```

**动态引脚复用** — 不仅依赖eFuse禁用JTAG(glitch有时可绕过eFuse)，而是在启动时立即将SWD/JTAG引脚复用为关键高频IO功能。如果攻击者试图保持引脚用于调试，设备功能性地自毁。

**主动PCB屏蔽** — 在PCB外层和BGA芯片正下方布设包含高频心跳信号的连续紧密编织走线网格。如果攻击者试图钻孔或切割PCB，网格断裂，心跳停止，MCU立即清零安全密钥库。

**蜜罐函数** — 创建看似加密例程的复杂数学密集型虚拟函数，大量引用 `AES_KEY_GEN_START` 等字符串。攻击者花费数周逆向这些"蜜罐"代码，而实际逻辑在别处以混淆的内联汇编执行。

---

