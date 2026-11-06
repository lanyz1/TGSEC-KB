## Step 7 — Managed Object Browser (MOB) — frequently leaks data

```bash
curl --max-time 30 --connect-timeout 10 -skI "https://$TARGET/mob"
# 401 → auth required (good for the defender)
# 200 → MOB exposed → can browse VMs, hosts, datastores, sessions without credentials in some misconfigs

# Auth'd MOB lets you walk the entire vSphere tree:
curl --max-time 30 --connect-timeout 10 -sk -u '<EMAIL-REDACTED>:<pw>' "https://$TARGET/mob/?moid=ServiceInstance&doPath=content"
```

---

