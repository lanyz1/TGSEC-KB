## Cost & Performance Tips

1. **Use `--max-turns`** in print mode to prevent runaway loops. Start with 5-10 for most tasks.
2. **Use `--max-budget-usd`** for cost caps. Note: minimum ~$0.05 for system prompt cache creation.
3. **Use `--effort low`** for simple tasks (faster, cheaper). `high` or `max` for complex reasoning.
4. **Use `--bare`** for CI/scripting to skip plugin/hook discovery overhead.
5. **Use `--allowedTools`** to restrict to only what's needed (e.g., `Read` only for reviews).
6. **Use `/compact`** in interactive sessions when context gets large.
7. **Pipe input** instead of having Claude read files when you just need analysis of known content.
8. **Use `--model haiku`** for simple tasks (cheaper) and `--model opus` for complex multi-step work.
9. **Use `--fallback-model haiku`** in print mode to gracefully handle model overload.
10. **Start new sessions for distinct tasks** — sessions last 5 hours; fresh context is more efficient.
11. **Use `--no-session-persistence`** in CI to avoid accumulating saved sessions on disk.

