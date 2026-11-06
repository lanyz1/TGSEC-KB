# IoT / 嵌入式安全测试（固件 / 硬件 / 协议 / 车联网）

> SRC/授权评估中 IoT 产品（路由器/摄像头/智能家居/MQTT 平台）的测试路径。偏硬件侧的面需要实体设备，SRC 场景常用的是固件分析与网络协议面。全部授权测试手法。

## 一、固件分析（不拆机也能做——SRC 最高性价比面）

### 1. 获取固件
```
厂商官网下载中心/升级页面
设备后台固件下载接口（未授权常可下）
OTA 更新包（抓包/逆向 App 找更新 URL）
App 内嵌固件（解 APK 提取，见移动端手册）
GitHub/论坛泄露
```

### 2. 解包与分析
```bash
binwalk -e firmware.bin                    # 自动提取（binwalk 全自动）
binwalk -Me firmware.bin                   # 递归提取
firmwalker firmware_dir                    # 自动找敏感信息（密码/密钥/硬编码）
# 手动: strings 找关键串
strings firmware.bin | grep -iE 'password|admin|secret|key|token'
# 文件系统挂载（如果是 squashfs/cpio）
unsquashfs rootfs.squashfs
```
### 3. 固化分析关注点
| 找什么 | 风险 |
|--------|------|
| 硬编码密码/密钥/后门账号 | 设备接管、云平台接入凭据 |
| 配置文件（busybox 密码 hash） | 弱口令/可破解 |
| 私有协议实现 | 协议绕过/重放 |
| Web 服务（busybox httpd/lua） | Web 漏洞（经典 Web 手法） |
| 云通信凭证（App 密钥/设备 ID） | 批量设备控制 |
| UPNP/MQTT 配置 | 未授权协议入口 |

**EMBA**（全自动嵌入式分析）一键跑：`emba -l firmware.bin`。

## 二、硬件接口（有实体设备时）

| 接口 | 手法 | 产出 |
|------|------|------|
| UART 串口 | 焊 3 针接 TTL 适配器（波特率盲扫常见 115200） | 直接 shell（root 常有） |
| JTAG/SWD | 调试接口读内存/Flash（OpenOCD） | 固件提取/调试 |
| SPI Flash | 夹子读芯片（flashrom） | 固件/配置提取 |
| I2C | 嗅探总线（逻辑分析仪） | 传感器/EEPROM 数据 |

**红线**：硬件操作只在自有/授权设备；读取不刷写（刷坏设备=事故）。

## 三、协议面（SRC 常见）

### MQTT（IoT 最广泛）
```bash
# Broker 发现
nmap -p 1883,8883,8083,8443,9001 --script mqtt-subscribe <t>
# 匿名订阅全部 topic（核心测试）
mosquitto_sub -h <broker> -p 1883 -t '#' -v
# 匿名发布（控制设备）
mosquitto_pub -h <broker> -t 'devices/XX/cmd' -m '{"cmd":"reboot"}'
```
**判定**：能订阅 `#` 全部消息 = 全局数据流泄露（传感器/位置/指令）；能发控制 topic = 设备控制（高危）。常见漏洞：无认证、弱口令、topic 无 ACL、明文 1883 无 TLS。

### CoAP
- `coap-client -m get coap://<t>/` 探测资源；默认资源枚举（`.well-known/core`）
- 无鉴权读写资源面

### BLE
```bash
# 扫描与连接（hci/hciconfig 或手机 nRF Connect）
hcitool lescan; gatttool -b <MAC> --interactive
# 特征读写无鉴权 → 控制设备/读取数据
```

### 其他
- ZigBee: 抓包（Zigbee 嗅探器）→ 网络密钥提取（实体面）
- Z-Wave/NFC/RFID: 重放/克隆面（Proxmark3 类，实体面）

## 四、车联网 / ICS（专项面）

| 面 | 协议 | 注意 |
|----|------|------|
| 车联网 | CAN/OBD-II/UDS | 需 OBD 接口实体；UDS 诊断服务枚举（0x22/0x2E 读写） |
| V2X | 通信伪造 | 类 Wi-Fi 面 |
| ICS | Modbus RTU/TCP | 功能码枚举、寄存器读写（**ICS 操作必须书面授权，误写会扰动生产**） |
|  | DNP3/OPC UA | 未授权面/协议漏洞 |
|  | PLC | 固件/程序上传下载面（高危，禁随意） |

**红线**：ICS/车联网任何写操作（写寄存器/刷 PLC）**必须书面授权 + 危险排除**——只做只读侦察或明确授权的演示。

## 五、2026 IoT 趋势

- Matter/Thread：新协议面（配网信息/网络密钥提取）
- 5G IoT / AIoT：eSIM/边缘计算面
- 暴露设备规模化漏洞利用（僵尸网络复现面——只评估补丁状态，不做利用）

## 六、完整流程（SRC 场景精简版）

```
1. 资产：品牌+型号 → FOFA/Shodan 搜公网暴露（port 1883/5683/80/8080/554 摄像头流）
2. 固件：官网/OTA 下载 → 解包 → 硬编码密钥/后门/Web 漏洞（最高产出）
3. Web 面：设备 Web 管理界面（经典 Web 测试全流程）
4. 移动 App：解 APK 找云接口/固件 URL/设备凭证（见移动端手册）
5. 协议面：MQTT/CoAP 匿名订阅与发布
6. 云面：设备云平台 API 越权（device_id 枚举 → 批量控制）
7. 报告：设备批量控制/敏感数据流泄露 = 高危起
```

## 七、纪律
- 固件分析最高性价比：不开机不碰硬件，先解包找钥匙
- MQTT 订阅测试用自己 broker 对照，不长期驻留监听
- 硬件/ICS 写操作严格红线；SRC 场景基本只做固件+网络+Web
- 设备控制类验证最小化（发一个无害指令如查询状态，不批量控制真实设备）