# Windows OpenVPN 安装/后台保活/健康检查(实测 2026-08)

跑分任务前置: VPN 必须连通, 且 **openvpn.exe 后台进程绝不 kill**(kill=任务失败, 用户明确纠正过)。

## 安装(winget)
```bash
winget install --id OpenVPNTechnologies.OpenVPN -e --accept-source-agreements --accept-package-agreements --silent
# 装到 C:\Program Files\OpenVPN\bin\openvpn.exe
```

## 启动连接(关键坑)

**--daemon 在 Windows 上不可用**(报 "daemon() failed or unsupported: The handle is invalid"), 必须用后台进程方式:

```bash
# 1. 配置文件复制到 config 目录(必须, 否则权限/路径问题)
cp ~/Downloads/task_*.ovpn "/c/Program Files/OpenVPN/config/task.ovpn"

# 2. 用 Hermes background=true 启动(不是 shell 的 & / nohup)
#    terminal(background=true), command:
cd "/c/Program Files/OpenVPN/bin" && ./openvpn.exe --config "../config/task.ovpn" --log "C:/Users/Administrator/ovpn.log"
```

## 验证连接
```bash
grep "Initialization Sequence Completed" /c/Users/Administrator/ovpn.log
curl -s -m 8 http://10.0.100.58   # → {"client_ip":"10.254.0.xx","status":"ok"} = VPN 通
tasklist | grep -i openvpn.exe     # 确认进程存活
```

## 保活要点(用户红线)

1. **绝不 kill openvpn 后台进程** — 一旦 kill, 所有容器 HTTP 000 失联, 跑分全废
2. VPN 断线判断: `curl http://10.0.100.58` 返回 HTTP:000 / 无 status:"ok"
3. 断线恢复: 重新 background=true 启动 openvpn.exe(同配置), 等待 Initialization Sequence Completed
4. 健康检查地址 10.0.100.58 只在 VPN 网内可达, 是可靠判据

## 其他坑

- 旧 openvpn 实例残留会报 "route exists"(无害, 已存在路由)
- ping 通 ≠ HTTP 通: TCP 可达但 HTTP 空回复 = 服务端无响应(健康检查以 status:"ok" 为准)
- MSYS/git-bash 的 /tmp 与 Windows /tmp 不一致: write_file 到 /tmp 后 curl 可能读不到, 用 C:/Users/... 绝对路径
