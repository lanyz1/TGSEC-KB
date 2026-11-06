## Gate 0 Validation

Before writing the report:

1. **What can the attacker DO right now?**
   - Authentication.asmx anonymous + no rate limit → **Critical** (unbounded credential validation; password spray + UPN format from NTLM = end-to-end ATO path)
   - Full ToolShell precondition chain (anon GET + anon FormDigest + anon POST + unencrypted VS) + EoL SP2013 → **Critical** (RCE via well-documented public exploit chain, no patch will ship)
   - NTLM Type-2 AD topology disclosure + default-Windows hostname → **Medium**
   - SP2013 EoL alone → **Medium-Low** (compliance / hygiene; bug-bounty programs vary — some accept, many reject)
   - `download.aspx` URL echo without confirmed Collaborator callback → **NOT SSRF — retract**

2. **Have you reproduced the full chain to attacker-attainable impact?**
   - For Authentication.asmx: 10-burst test with uniform timing (proves no rate limit) is sufficient. Don't actually crack a credential.
   - For ToolShell: precondition chain (steps a+b+c) is sufficient. Don't deliver a malicious payload.
   - For NTLM: AV-pair decode showing AD-topology fields is sufficient.

3. **Can you reproduce in <10 minutes from a clean shell?**
   - Authentication.asmx: 2 curl commands.
   - ToolShell precondition: 3 curl commands.
   - NTLM Type-2: 1 Python snippet (the AV-pair decoder).

---

