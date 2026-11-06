## Subdomain Takeover

### Detection
```bash
# Check for dangling CNAMEs
cat /tmp/subs.txt | dnsx -silent -cname -resp | grep -i "CNAME" | tee /tmp/cnames.txt
# Look for CNAMEs to: github.io, heroku.com, azurewebsites.net, netlify.app, s3.amazonaws.com

# Automated takeover detection
nuclei -l /tmp/subs.txt -t ~/nuclei-templates/takeovers/ -o /tmp/takeovers.txt
```

### Quick-Kill Fingerprints
```
"There isn't a GitHub Pages site here"  -> GitHub Pages
"NoSuchBucket"                          -> AWS S3
"No such app"                           -> Heroku
"404 Web Site not found"                -> Azure App Service
"Fastly error: unknown domain"          -> Fastly CDN
"project not found"                     -> GitLab Pages
"It looks like you may have typed..."   -> Shopify
```

### Impact Escalation
- Basic takeover: serve page under target.com subdomain -> Low/Medium
- + Cookies: if target.com sets cookie with domain=.target.com -> credential theft -> High
- + OAuth redirect: if sub.target.com is a registered redirect_uri -> ATO chain -> Critical
- + CSP bypass: if sub.target.com is in target's CSP -> XSS anywhere -> Critical

