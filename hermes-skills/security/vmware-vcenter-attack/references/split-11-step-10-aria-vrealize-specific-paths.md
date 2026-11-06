## Step 10 — Aria / vRealize specific paths

```bash
# vRealize Operations Manager
curl --max-time 30 --connect-timeout 10 -sk "https://$TARGET/suite-api/api/versions"
curl --max-time 30 --connect-timeout 10 -sk "https://$TARGET/casa/nodes/thumbprints"

# Aria Automation
curl --max-time 30 --connect-timeout 10 -sk "https://$TARGET/csp/gateway/am/api/about"
curl --max-time 30 --connect-timeout 10 -sk "https://$TARGET/cluster-administration/api/health"

# vRealize Orchestrator
curl --max-time 30 --connect-timeout 10 -sk "https://$TARGET/vco/api/about"
curl --max-time 30 --connect-timeout 10 -sk "https://$TARGET/vco-controlcenter/api/health"
```

---

