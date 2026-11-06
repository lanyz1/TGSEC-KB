## Prototype architecture: single-file HTML SPA
- One HTML file: all CSS in `<style>`, all JS in `<script>`, zero external deps (user is in China — Google Fonts/CDNs are blocked)
- Views: `<section class="view" id="view-<route>">` inside `<main>`; `show(route)` toggles `.active`; `body.auth-mode` hides `.nav`/`.topbar` for login/register/onboarding screens
- Hash routing: `history.replaceState(null,'','#/'+route)` + `hashchange` listener so refresh keeps the page
- Shared shell: sidebar + topbar; each page has its own `.page-head` (h2 + action buttons)
- Include working interactions: toasts, modals (delete confirm, cashier), countdown, inline stock steppers, batch-action bar, chat session switching, tab panels, step wizards (JS show/hide), SVG chart with range toggle + hover tooltip
- Verify: `browser_navigate file://…` → sweep every route via `browser_console` (`routes.forEach(r=>{try{show(r)}catch(e){…}})`), confirm `js_errors` empty → `open_preview`

