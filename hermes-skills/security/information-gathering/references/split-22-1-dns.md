## 1. 被动枚举(不发 DNS 请求)
```bash
# Subfinder
subfinder -d target.com -o subdomains.txt
subfinder -d target.com -all -o subdomains.txt -v   # 多数据源(填 API key 更全)
# 配置文件 ~/.config/subfinder/provider-config.yaml: Shodan/Censys/SecurityTrails/VirusTotal/GitHub key

# Amass(最全面较慢)
amass enum -passive -d target.com -o subs.txt
amass enum -d target.com -r 8.8.8.8,1.1.1.1

# OneForAll(中文功能全)
git clone https://github.com/shmilylty/OneForAll.git && cd OneForAll
pip install -r requirements.txt
python3 oneforall.py --target target.com run   # 结果 results/target.com.csv

# crt.sh 证书透明度(零依赖首选)
curl -s "https://crt.sh/?q=%.target.com&output=json" | \
  jq -r '.[].name_value' | sort -u | grep -v '[*]' > ct_subdomains.txt
```

