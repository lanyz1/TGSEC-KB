## Cache Poisoning / Web Cache Deception
- [ ] Test `X-Forwarded-Host`, `X-Original-URL`, `X-Rewrite-URL` -- unkeyed headers reflected in response
- [ ] Parameter cloaking (`?param=value;poison=xss`)
- [ ] Fat GET (body params on GET requests)
- [ ] Web cache deception (`/account/settings.css` -- trick cache into storing private response)
- [ ] Param Miner (Burp extension) -- auto-discovers unkeyed headers

