## XSS -- Cross-Site Scripting

### XSS Sinks (grep for these)
```javascript
// HIGH RISK
innerHTML = userInput
outerHTML = userInput
document.write(userInput)
eval(userInput)
setTimeout(userInput, ...)    // string form
setInterval(userInput, ...)
new Function(userInput)

// MEDIUM RISK (context-dependent)
element.src = userInput        // JavaScript URI possible
element.href = userInput
location.href = userInput
```

### XSS Chains (escalate from Medium to High/Critical)
- XSS + sensitive page (banking, admin) = High
- XSS + CSRF token theft = CSRF bypass -> Critical action
- XSS + service worker = persistent XSS across pages
- XSS + credential theft via fake login form = ATO
- XSS in chatbot response = stored XSS chain

