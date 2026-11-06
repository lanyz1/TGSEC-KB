## 7. Recover the contract from the client binary before writing payloads

For Android targets, APK string de-obfuscation turns guessed field names into exact ones:

```python
KEYS = [61945, 41027, 37077, 65535]
def se_v1(s):  # s = the decoded Java string literal passed to _se_v1("...")
    return ''.join(chr(ord(c) ^ KEYS[i % 4]) for i, c in enumerate(s))
```

- Extract every `_se_v1("...")` literal, unescape Java escapes, then XOR. Decrypt the **whole
class set**, not just the login activity — the base URL, the signing config and the parameter
names live in different classes.
- Filter to printable codepoints before printing or the dump dies mid-scan on surrogate pairs.
- Highest-value outputs: the `addParams("…")` field names, the default server list (§6), and any
AES key/IV pair used for request encryption.
- **A client-side-encrypted field must be re-implemented from a CAPTURED request, and the padding is
the silent killer.** Verify against one real submission (browser interception, §2) before any spray:
on the same key/IV, zero-byte padding (`.ljust(16, b'\\x00')`) and PKCS7 produce different
ciphertexts, and the wrong one answers the ordinary invalid-password string for EVERY candidate — a
'0 hits' run is then not evidence of anything. Measured: PKCS7 logged in where zero-pad returned
INVALID_PASSWORD; re-testing the high-value candidates the broken engines had rejected produced ~10
confirmed hits, several of them chat-leaked credentials previously marked 'invalid'. After any such
fix, audit every spray engine (`grep -A3 'def enc' *.py`) and re-run the top candidates it rejected.

**Server side too — clone the admin framework when the panel is an open-source stack.** Chinese
admin panels (go-wind-admin and siblings) answer their auth questions faster from the repo than
from black-box probing: seed credentials (constants files — e.g. go-wind-admin currently seeds
`admin` / `Abcd@1234`, its older plain-`admin` default retired for failing the framework's own
complexity policy), the error-normalization map (which failure classes merge into one string — this
decides which oracles survive), rate-limit dimensions (IP vs IP+username — still re-measure on the
deployment), and password-policy size. Forks diverge from upstream, and the deployed front-end
bundle tells you which fork is actually live.

