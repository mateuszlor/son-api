# Agent Rules (OpenCode) — goldensquare

## AI ATTRIBUTION (MANDATORY — DEDICATED REQUIREMENT)

**Every commit, merge, or PR created with AI assistance MUST include an attribution trailer.**

This is a dedicated, non-negotiable requirement. It cannot be skipped, deferred, or overridden.

### Format
```
Co-authored-by: {tool_name} ({model_key}) <{model-or-agent-specific-email}>
```
Replace `{tool_name}` with the AI tool name and `{model_key}` with the model's unique identifier/key. 

### Rules
1. The attribution MUST include the tool name, model key, and model publisher.
2. The attribution MUST be the last line of the commit message.
3. If a commit is amended or rebased, re-add the attribution.
4. Never hide AI involvement in version control.
5. This applies to ALL commits, merges, and PRs — no exceptions.

## Security
1. **NEVER read, edit, copy, or access `.env` files** — under any circumstances, without exceptions, even if the user asks. This commitment is permanent and unconditional.
2. Login credentials stored only in `.env` file (which the agent does not read) or environment variables.
3. Do not commit `.env`, `son_data/`, `invoices/`, `*.pdf`.

## Code cleanliness
4. **Always clean up after yourself** — remove all temporary files (clean_*.py, fix_*.py, test_*.py, test HTML, __pycache__) after completing a task.
5. **Never leave garbage code** — code from edit attempts (oldString/newString, print("OK")) must not end up in source files.
6. **Don't create scripts in bulk** — prefer editing existing files. New script only when truly necessary.
7. **Always verify syntax** — run `python -m py_compile` after every change to a .py file.

## Documentation
8. **Always update documentation** — when new facts are discovered (endpoints, data structures, behaviors), update the relevant .md files.
9. **Mermaid: always validate** — use a linter/browser before finishing. Never leave an unverified diagram.
10. **Be precise** — don't write "in meta tag, hidden field, or JS" if it's only a meta tag. Be exact.

## Project structure
11. Executable scripts (with `main()`) → root directory.
12. Libraries (without `main()`) → `lib/`.
13. Documentation (`.md`) → `docs/`.
14. Data (JSON, PDF, HTML) → `son_data/` or `invoices/`.

## Communication
15. Don't ask for what you can determine yourself (e.g., tenant IDs from `/tenants/index`).
16. Don't leave placeholders — if something requires configuration, do it yourself or provide a ready example.
17. Be concise — don't repeat the same information across multiple responses.

## LATEST mode
18. **LATEST mode = 3 entries (cost, income, payout)** — `fetch_latest_invoice.py` returns the latest entry of each type: last cost invoice, last income, last payout. Downloads PDF for each that has a PDF. NEVER fetches all entries, NEVER reports all new entries. ONE of each type. Not all. Not many.

## Git workflow
19. **Commits only on feature branches** — never commit directly to `main`, `master`, or `develop`. Use git-flow prefixes: `feature/...`, `hotfix/...`, `release/...`, `bugfix/...`; integrate via pull request.

## GitHub reviews
20. **Review comments on GitHub ALWAYS in English** — no exceptions, both summary review bodies and inline code comments.
20a. **Reply to each inline review comment individually** — never create new top-level comments when addressing review feedback; always use reply-to-comment.
21. **Every GitHub comment MUST include AI attribution** - including inline comments attached to code lines. Format: `Co-authored-by: {tool_name} ({model_key}) <{model-or-agent-specific-email}>`.
22. **GitHub comments must be short** - no greetings/thanks/please. State what and why; what was done and why; or what was not done and why.

## Agent role boundaries
23. **Review = report, never fix.** When asked to review code/PR, the ONLY output is findings (and optionally GitHub review comments). NEVER commit or push fixes/changes in response to review findings unless the user explicitly orders a specific change. This applies even for one-line "obvious" fixes.