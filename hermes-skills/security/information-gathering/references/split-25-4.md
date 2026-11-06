## 4. 存活探测与指纹
```bash
cat subdomains.txt | httpx -silent -o live_hosts.txt -threads 50 -timeout 5
cat subdomains.txt | httpx -silent -title -tech-detect -status-code -o live_full.txt
# httprobe: cat subdomains.txt | httprobe | sort -u > live.txt
```

