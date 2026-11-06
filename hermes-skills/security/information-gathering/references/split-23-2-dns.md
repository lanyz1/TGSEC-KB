## 2. 主动 DNS 爆破
```bash
dnsx -l wordlist.txt -d target.com -o dnsx_results.txt -r 8.8.8.8 -rl 500
# massdns: massdns -r resolvers.txt -t A -o S -w out.txt brute_list.txt
# ffuf: ffuf -w subdomains-top1million-5000.txt -u http://FUZZ.target.com -mc 200,301,302,403
# 常用字典: SecLists /Discovery/DNS/: subdomains-top1million-110000.txt / -5000.txt / dns-Jhaddix.txt
```

