## XSS Tips & Tricks
A `400`, `404`, or `500` response to a payload is only an input-handling signal. It does not prove sanitization or a vulnerability. Repeat with a unique benign marker, compare status, headers, and body against a baseline, classify the output context, and confirm execution in a current browser before reporting.

