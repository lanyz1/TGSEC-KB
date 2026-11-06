## Precondition gate (standing user rule)

Credential spraying is a LAST resort, never an opening move. Do not start a spray unless the user
named it for this target, or the non-credential surface is exhausted (unauthorized access, IDOR,
business logic, JS-discovered APIs, session handling, side ports, injection).

- A captcha oracle, an enumeration oracle, or "no rate limit observed" does NOT license a spray;
it only lowers its cost. Priority is unchanged.
- Ten to twenty common passwords with no hit means the password policy is healthy. Stop and pivot
to logic/session surfaces; do not start a long background dictionary run.
- When the user says stop spraying: kill the running spray processes immediately, and state in the
report that common weak passwords were tested and spraying was stopped on request.
- Model the target's lockout/limit economics (§5) BEFORE committing to a dictionary. A run that
cannot finish inside the window is worse than no run: it costs hours and yields nothing.

