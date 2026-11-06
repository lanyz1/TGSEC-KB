## 6 Key Patterns from Top Reports
1. **Feature Complexity = Bug Surface** -- imports, integrations, multi-tenancy, multi-step workflows
2. **Developer Inconsistency = Strongest Evidence** -- `timingSafeEqual` in one place, `===` elsewhere
3. **"Else Branch" Bug** -- proxy/gateway passes raw token without validation in else path
4. **Import/Export = SSRF** -- every "import from URL" feature has historically had SSRF
5. **Secondary/Legacy Endpoints = No Auth** -- `/api/v1/` guarded but `/api/` isn't
6. **Race Windows in Financial Ops** -- check-then-deduct as two DB operations = double-spend

---

# PHASE 3: HUNT

