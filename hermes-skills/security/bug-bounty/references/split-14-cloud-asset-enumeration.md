## Cloud Asset Enumeration
```bash
# Manual S3 brute
for suffix in dev staging test backup api data assets static cdn; do
  code=$(curl --max-time 30 --connect-timeout 10 -s -o /dev/null -w "%{http_code}" "https://${TARGET}-${suffix}.s3.amazonaws.com/")
  [ "$code" != "404" ] && echo "$code ${TARGET}-${suffix}.s3.amazonaws.com"
done
```

