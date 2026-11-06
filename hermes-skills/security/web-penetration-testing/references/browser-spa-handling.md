# Browser Tool SPA Handling Notes

## Headless Chrome with React SPAs (Umi.js)

EC Markets IB dashboard (`ib.ecmarkets.com.au`) uses Umi.js React SPA.

### Working Login Flow
```python
# Step 1: Navigate to locale-prefixed login page
browser_navigate("https://ib.ecmarkets.com.au/zh-CN/userSign/login")

# Step 2: Fill credentials
browser_type(ref="e14", text="<EMAIL-REDACTED>")    # Email field
browser_type(ref="e16", text="password123")        # Password field

# Step 3: Click login
browser_click(ref="e10")                           # Login button

# Step 4: Verify login
browser_console("window.location.href")            # Should show /dashboard
```

### Critical SPA Pitfalls

1. **Locale prefix required**: Always use `/zh-CN/` or `/en-US/` path prefix. Bare domain redirects to WordPress site which can't render the React SPA properly.

2. **SPA state loss**: After navigating to a non-existent route (e.g., `/en-US/commission/chain` when the actual route is different), the SPA cache corrupts and the page shows blank with a single clickable element. **Fix**: Navigate back to `/zh-CN/userSign/login` to force full reload.

3. **Anti-bot detection**: The SPA may fail to render in headless Chrome, showing "加载中" (Loading...) indefinitely. This is a browser fingerprinting issue, not a login failure. The session is still valid — API calls will work from curl with the right token.

4. **browser_console restrictions**: `document.cookie`, `localStorage`, `fetch()` calls are blocked. Use `window.location.href`, `document.title`, `document.body.innerText` instead for safe expressions.

5. **Performance API**: `performance.getEntriesByType('resource')` works to list API calls made by the SPA, but does NOT expose request headers or response bodies.

### Recommended Strategy

1. Login via browser tools
2. Extract API paths from `performance.getEntriesByType('resource')`
3. Use curl with token to make API calls (browser's cookie/token context doesn't carry to curl)
4. When token expires, re-login via browser tools and check the new API paths

## See Also
- `references/stateless-vanillajs-spa-auth.md` — for SPAs that use NO tokens/cookies (localStorage-only session, credentials on every request)
