## 6. 完整流程串联(一键)
```bash
domain="target.com"
subfinder -d $domain -o subs_sf.txt -all -silent
amass enum -passive -d $domain -o subs_amass.txt 2>/dev/null
curl -s "https://crt.sh/?q=%.${domain}&output=json" | jq -r '.[].name_value' | grep -v '[*]' | sort -u > subs_ct.txt
cat subs_sf.txt subs_amass.txt subs_ct.txt | sort -u > all_subs.txt
cat all_subs.txt | httpx -silent -status-code -title -tech-detect -o live_hosts.txt
subjack -w all_subs.txt -t 50 -timeout 30 -o takeover.txt -ssl
```

