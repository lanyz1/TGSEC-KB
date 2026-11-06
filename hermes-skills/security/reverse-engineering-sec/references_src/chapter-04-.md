## 4. 固件逆向工程

### 4.1 固件提取技术

**SWD和JTAG（前门攻击）** — 如果调试端口在生产环境中保持激活，使用Segger J-Link或OpenOCD可在几秒内转储整个闪存：

```bash
# OpenOCD转储ARM固件
openocd -f interface/jlink.cfg -f target/stm32f4x.cfg \
    -c "init" \
    -c "halt" \
    -c "flash read_bank 0 firmware_dump.bin 0 0x100000" \
    -c "shutdown"
```

**Flash转储（脱焊方法）** — 对使用外部SPI/I2C闪存芯片的系统，使用热风返修台脱焊芯片，放入CH341A读取器：

```bash
# 使用CH341A和flashrom读取SPI闪存
flashrom -p ch341a_spi -r firmware_dump.bin
```

**SPI嗅探（传输中拦截）** — 对BGA封装闪存，使用逻辑分析仪（Saleae）连接MCU和闪存芯片之间的走线，在设备重启时捕获固件加载过程：

```text
SPI嗅探连接:
  逻辑分析仪CH1 → SPI CLK
  逻辑分析仪CH2 → SPI MOSI (MCU→Flash)
  逻辑分析仪CH3 → SPI MISO (Flash→MCU)
  逻辑分析仪CH4 → SPI CS

触发条件: CS下降沿(开始传输)
捕获: 完整固件从Flash加载到MCU RAM的数据
```

### 4.2 固件分析工具链

| 工具 | 特点 | 适用场景 |
|---|---|---|
| **Ghidra** | 自动反编译ARM/MIPS/x86为C-like伪代码 | 通用固件逆向 |
| **IDA Pro** | 冷门微控制器处理器模块支持 | 特殊架构固件 |
| **Binary Ninja** | 极快UI和强大IL | 快速分析 |
| **Radare2/Cutter** | 命令行驱动，脚本化 | CI/CD管道集成 |
| **binwalk** | 固件提取和特征扫描 | 固件解包 |

```bash
# binwalk固件提取
binwalk -e firmware.bin
# 递归提取嵌套文件系统
binwalk -eM firmware.bin
# 扫描加密签名
binwalk -S firmware.bin

# 在提取的文件系统中查找敏感信息
find _firmware.bin.extracted/ -type f -name "*.conf" -o -name "*.cfg" -o -name "*.key"
grep -rn "password\|admin\|root\|secret" _firmware.bin.extracted/
# 查找硬编码凭据
strings _firmware.bin.extracted/squashfs-root/bin/httpd | grep -i "pass\|key\|token"
```

### 4.3 硬件调试工具

| 工具 | 功能 | 价格区间 |
|---|---|---|
| 逻辑分析仪(Saleae) | 抓取UART/SPI通信信号 | $500+ |
| OpenOCD | JTAG接口调试ARM芯片 | 开源 |
| Bus Pirate | 万能硬件调试(I2C/SPI等) | $30-50 |
| JTAGulator | 发现和识别JTAG接口 | $50-70 |
| Glasgow Interface Explorer | 多协议硬件接口 | $100+ |
| ChipWhisperer | 侧信道分析和故障注入 | $300+ |

### 4.4 嵌入式设备调试复活

通过在RDP（读取保护）检查期间进行glitch来重新启用调试：

```text
调试复活流程:
  1. 在启动期间捕获功耗轨迹
  2. 识别安全检查时序(功耗轨迹中的特征模式)
  3. 配置glitch参数:
     - 宽度: 10-50ns
     - 偏移: 相对于时钟边沿的精确位置
     - 重复: 迭代直到成功绕过
  4. 通过调试接口提取固件

所需设备: ChipWhisperer/类似glitch平台 + 示波器 + 目标板修改(电容移除)
```

---

