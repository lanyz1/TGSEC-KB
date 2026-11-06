## Fake-Auth-Server Pattern (when redirect is viable)
- Swap 3 RSA public keys in the client to your own keypair (equal-length 271-byte PEM blocks are replaceable).
- Run a local HTTP fake server on the target port (e.g. 18888) that decrypts the client's RSA+AES request and returns `{"Status":1,"VipTime":<2099>}`.
- Redirect traffic: hosts entry (if app uses a domain), or Frida sockaddr rewrite (if hardcoded IP). Domain fallback: block the primary IP with firewall so the app falls back to its backup domain → hosts → localhost.
- Keep-alive timing: connect redirects only work if the hook is present BEFORE the keep-alive socket is created (early attach / fast_attach).

