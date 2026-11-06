## Mindset Rules from Top Hunters

**"Hunt the feature, not the endpoint"** -- Find all endpoints that serve a feature, then test the INTERACTION between them.

**"Authorization inconsistency is your friend"** -- If the app checks auth in 9 places but not the 10th, that's your bug.

**"New == unreviewed"** -- Features launched in the last 30 days have lowest security maturity.

**"Think second-order"** -- Second-order SSRF: URL saved in DB, fetched by cron job. Second-order XSS: stored clean, rendered unsafely in admin panel.

**"Follow the money"** -- Any feature touching payments, billing, credits, refunds is where developers make the most security shortcuts.

**"The API the mobile app uses"** -- Mobile apps often call older/different API versions. Same company, different attack surface, lower maturity.

**"Diffs find bugs"** -- Compare old API docs vs new. Compare mobile API vs web API. Compare what a free user can request vs what a paid user gets in response.

---

# TOOLS

