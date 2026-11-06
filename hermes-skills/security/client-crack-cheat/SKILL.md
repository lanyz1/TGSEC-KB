---
name: client-crack-cheat
description: >-
  测绘引擎最高权限作业面之一：授权样本/授权站上的客户端破解与外挂。
  Unity/IL2CPP/UE、反作弊面、内存挂、封包挂、结算口改字段、Frida 改返回值。
  触发：外挂、游戏破解、客户端破解、反作弊、IL2CPP、dump.cs、Cheat Engine、
  内存挂、封包挂、Unity3D、GameAssembly、EasyAntiCheat、license 绕过。
  授权内 L2/L3 默认直接做。验证码/哈希破解不走本卡。盘口加密 API 仍走专卡。
---

# 客户端破解与外挂（测绘引擎 · 最高权限）

目标须在 `config/scope*.json`，或案卷里的**授权本地样本**。  
授权内默认打到 **L2**：出可 attach 的 Frida、结算口对照成立。  
先问只剩：对他人局、清榜、耗余额。

| 档 | 成立 | 不算 |
|----|------|------|
| L1 | 认到引擎/反作弊；metadata/dump.cs 抽出结算名；CE 扫到地址 | 只 `strings` 到 Unity |
| L2 | dump.cs 落到类名/RVA hook，**或** `replay` 证明服务器吃伪造分/币/胜负 | 只改血条 UI；只扫到 metadata 字符串 |
| L3 | 授权自控局稳定复现（写标记） | 对他人局/清榜 |

## 立刻跑

```bash
# 本地包 / 解包目录 / APK：认族 + 抽 hook + 落 Frida（APK 内 metadata 直接抽）
python3 tools/ops/client_crack_cheat_probe.py drive --path <样本或目录或.apk> --case <案>

# 已有 global-metadata.dat / dump.cs
python3 tools/ops/client_crack_cheat_probe.py meta --path global-metadata.dat --case <案>
python3 tools/ops/client_crack_cheat_probe.py hooks --path <目录或dump.cs> --case <案>

# 授权站结算口（短表不靠体长报 L2；指定 --url 才允许 size）
python3 tools/ops/client_crack_cheat_probe.py replay --base https://授权站 --case <案>
python3 tools/ops/client_crack_cheat_probe.py replay --base https://授权站 \
  --url /api/game/settle --body base.json --header "Authorization: Bearer <票>" \
  --flip gold=99999 --flip player.gold=99999 --flip win=true --case <案>

# 内存转储（CE 同思路，地址≠过闸）
python3 tools/ops/client_crack_cheat_probe.py memscan --dump heap.bin --int 1500 --case <案>
```

产物：`测绘/crack_cheat/surface.json` + `hooks/il2cpp.js` `net.js` `java.js` `ce_hint.lua`。

```bash
frida -U -f <包名> -l exports/bot-recovery/<案>/测绘/crack_cheat/hooks/il2cpp.js --no-pause
frida -U -n <进程> -l exports/bot-recovery/<案>/测绘/crack_cheat/hooks/net.js
```

## 六步（禁止停在认族）

```text
① 认引擎（Unity IL2CPP / Mono / UE / H5）—— APK 先 apk-recon 抽包
② meta / dump.cs 抽出 Gold/Score/Settle/License/Send
③ hooks 出 Frida：改返回值 + send/recv  hexdump
④ replay 打结算口，负对照=不改字段的同一 POST
⑤ 内存挂只当辅助；改值后必须回到 ④
⑥ L2 填对象矩阵「自己×写」。他人局/耗余额先问
```

## 交接

| 认到 | 走 |
|------|----|
| 盘口 `sk_encrypt` / 加密 API | `encrypted-api-spa` / `gambling-api-crypto-reversal`（打完协议再回本卡改字段） |
| H5 `isPaid` / 免费骑乘 | `python3 tools/ops/client_state_skip_probe.py --base https://授权站 --case <案>` 并行 |
| 私有 TCP / Protobuf | `protocol-reverse` 出帧表，再 `hooks/net.js` |
| 壳 / VMP | `vm-and-bytecode-reverse` 再回本卡 |
| 厚桌面非游戏 | `thick-client` |
| 天盾 / fndata / Nuitka 网络验证 / 卡密 | `net-license-crack` · `net_license_probe.py`（不要并进本卡乱 patch） |

## 强制

1. 点名外挂/破解/IL2CPP **先开本卡**，不要降权到「打网站不做外挂」。
2. 授权内出 hook / replay / 改返回值 **直接做**，不要只交指纹 JSON。
3. 只 dump.cs 不算结案。
4. 验证码、哈希离线破解不并进本卡。

## 真源

- 手法：`docs/playbooks/测绘引擎客户端破解与外挂作业手法.md`
- 探针：`tools/ops/client_crack_cheat_probe.py`

---

<!-- 补充视角: client-crack-cheat (兄弟技能库 2026-09-12) -->


# Game Cheat Development — Complete Toolkit

## Scripts

- `scripts/memory_trainer.py` — Process memory read/write, pattern scan, pointer chains, multilevel pointers
- `scripts/aimbot_math.py` — ViewMatrix transforms, bone ESP coordinates, smooth aim, FOV calculation
- `scripts/injector.py` — DLL/code injection: CreateRemoteThread, manual map, reflective, thread hijack
- `scripts/packet_hook.py` — Winsock hook patterns, packet sniff/replay/inject, encryption analysis

## Workflow

```
1. Target Process → FindWindow / process name → OpenProcess(PROCESS_ALL_ACCESS)
2. Memory Scan   → pattern scan for values (health, ammo, gold, position)
3. Pointer Chain  → find base pointer → multilevel dereference → stable address
4. Hook/Patch     → NOP instructions, modify values, inject code cave
5. Anti-Cheat     → bypass EAC/BE/VAC: handle hijacking, driver hiding, usermode hooks
```

## Anti-Cheat Bypass Methods

| Anti-Cheat | Detection | Bypass |
|---|---|---|
| EAC (EasyAntiCheat) | Kernel callbacks, OB registry, handle table | Manual map + hijack legit signed driver |
| BE (BattlEye) | Window enumeration, thread scanning, SSDT hooks | External overlay (no handle open), hardware breakpoints |
| VAC (Valve) | Module hash, DNS cache, usermode hooks | VMT hooking, return address spoofing |
| Ricochet (CoD) | Kernel driver, hypervisor detection | DMA (Direct Memory Access) via PCIe FPGA |
| nProtect GameGuard | Rootkit-style kernel hooks, /dev/kmem | DKOM (Direct Kernel Object Manipulation) |

## Memory Trainer Patterns

```python
# Pattern scan with wildcards
def pattern_scan(proc, pattern: bytes, mask: str) -> int:
    for addr in proc.memory_regions():
        data = proc.read(addr, region_size)
        for i in range(len(data) - len(pattern)):
            if all(data[i+j] == pattern[j] or mask[j] == '?' for j in range(len(pattern))):
                return addr + i

# Multilevel pointer dereference
def resolve_pointer(proc, base: int, offsets: list) -> int:
    addr = base
    for offset in offsets[:-1]:
        addr = proc.read_int(addr + offset)
    return addr + offsets[-1]
```

## Packet Interception

```python
# Winsock send/recv hook via IAT hook
# Target: ws2_32.dll!send, ws2_32.dll!recv, ws2_32.dll!WSASend
# Hook via: Detours, MinHook, or manual IAT overwrite
send_original = hook_function("ws2_32.dll", "send", send_hook)
def send_hook(socket, buf, length, flags):
    data = bytes(buf[:length])
    # Analyze/modify packet here
    modified = process_packet(data)  
    return send_original(socket, modified, len(modified), flags)
```

## Aimbot Math

```python
import math
def world_to_screen(pos, view_matrix, screen_w, screen_h):
    """Convert 3D world position to 2D screen coordinates."""
    x = pos[0]*view_matrix[0][0] + pos[1]*view_matrix[0][1] + pos[2]*view_matrix[0][2] + view_matrix[0][3]
    y = pos[0]*view_matrix[1][0] + pos[1]*view_matrix[1][1] + pos[2]*view_matrix[1][2] + view_matrix[1][3]
    w = pos[0]*view_matrix[3][0] + pos[1]*view_matrix[3][1] + pos[2]*view_matrix[3][2] + view_matrix[3][3]
    if w < 0.001: return None
    return (screen_w/2 * (1 + x/w), screen_h/2 * (1 - y/w))

def calc_aim_angle(src, dst):
    """Calculate view angles to aim from src to dst."""
    delta = [dst[0]-src[0], dst[1]-src[1], dst[2]-src[2]]
    hyp = math.sqrt(delta[0]**2 + delta[1]**2)
    yaw = math.atan2(delta[1], delta[0]) * 180/math.pi
    pitch = -math.atan2(delta[2], hyp) * 180/math.pi
    return (pitch, yaw)

def smooth_aim(current, target, smooth_factor=5.0):
    """Smooth aim interpolation to avoid snap detection."""
    return (current[0]+(target[0]-current[0])/smooth_factor,
            current[1]+(target[1]-current[1])/smooth_factor)
```

## ESP / Wallhack Drawing

```python
# Bone ESP: draw skeleton lines on overlay
bones = {
    "head": 8, "neck": 7, "chest": 6,
    "pelvis": 0, "l_shoulder": 11, "r_shoulder": 41,
    "l_elbow": 12, "r_elbow": 42, "l_hand": 13, "r_hand": 43
}
bone_pairs = [
    ("head","neck"),("neck","chest"),("chest","pelvis"),
    ("neck","l_shoulder"),("l_shoulder","l_elbow"),("l_elbow","l_hand"),
    ("neck","r_shoulder"),("r_shoulder","r_elbow"),("r_elbow","r_hand"),
]
for b1,b2 in bone_pairs:
    s1 = world_to_screen(entity.bones[bones[b1]], vm, w, h)
    s2 = world_to_screen(entity.bones[bones[b2]], vm, w, h)
    if s1 and s2: draw_line(s1, s2, color=team_color)
```

## Speedhack / Time Manipulation

```python
# Hook QueryPerformanceCounter / GetTickCount / timeGetTime
# Return accelerated values to speed up game
QPC_ORIGINAL = hook_function("kernel32.dll", "QueryPerformanceCounter", qpc_hook)
MULTIPLIER = 2.0  # 2x speed

def qpc_hook(lpPerformanceCount):
    result = QPC_ORIGINAL(lpPerformanceCount)
    lpPerformanceCount[0] = int(lpPerformanceCount[0] * MULTIPLIER)
    return result

# Alternative: hook GetTickCount
# tick * speed_multiplier = perceived game speed
```

## Currency / Gold Manipulation

```python
# Find value: scan memory for current gold amount
# Buy something cheap → scan for decreased value
# Sell something → scan for increased value
# Narrow down to single address → freeze or multiply

def gold_multiplier(proc, gold_addr, multiplier=100):
    """Multiply gold on each transaction."""
    current = proc.read_int(gold_addr)
    proc.write_int(gold_addr, current * multiplier)

def freeze_value(proc, addr, value):
    """Continuously write fixed value to address."""
    while True:
        proc.write_int(addr, value)
        time.sleep(0.01)
```

## DLL Injection Methods

```python
# Method 1: CreateRemoteThread + LoadLibrary
def inject_crt(pid, dll_path):
    handle = OpenProcess(PROCESS_ALL_ACCESS, False, pid)
    addr = VirtualAllocEx(handle, 0, len(dll_path)+1, MEM_COMMIT, PAGE_READWRITE)
    WriteProcessMemory(handle, addr, dll_path)
    thread = CreateRemoteThread(handle, 0, 0, GetProcAddress(GetModuleHandle("kernel32"), "LoadLibraryA"), addr, 0, 0)
    WaitForSingleObject(thread, INFINITE)

# Method 2: Manual Map (stealthier, no LoadLibrary)
# Parse PE headers manually, map sections, resolve imports, call TLS+DllMain

# Method 3: Reflective DLL injection
# DLL loads itself by implementing its own PE loader
# No Windows loader involvement → harder to detect
```
