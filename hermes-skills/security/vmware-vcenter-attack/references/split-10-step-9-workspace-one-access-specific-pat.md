## Step 9 — Workspace ONE Access specific paths

```bash
# Metadata
curl --max-time 30 --connect-timeout 10 -sk "https://$TARGET/SAAS/auth/saml/response"
curl --max-time 30 --connect-timeout 10 -sk "https://$TARGET/SAAS/auth/wsfed/services/idp"
curl --max-time 30 --connect-timeout 10 -sk "https://$TARGET/SAAS/jersey/manager/api/health"
curl --max-time 30 --connect-timeout 10 -sk "https://$TARGET/catalog-portal/services/airwatch/identifiers"

# Login page
curl --max-time 30 --connect-timeout 10 -sk "https://$TARGET/SAAS/login/0"
```

---

