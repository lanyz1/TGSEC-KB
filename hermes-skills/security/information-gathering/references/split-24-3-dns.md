## 3. DNS 历史与旁站
```bash
# SecurityTrails(API key)
curl -s "https://api.securitytrails.com/v1/domain/target.com/subdomains" -H "APIKEY: <key>" | jq '.subdomains[]'
# VirusTotal
curl "https://www.virustotal.com/vtapi/v2/domain/report?apikey=<REDACTED>" | jq '.subdomains[]'
# 同 IP 旁站
curl "https://api.hackertarget.com/reverseiplookup/?q=1.2.3.4"
```

