# Working on TrustSQL

Read `PRODUCT.md`, `docs/ARCHITECTURE.md`, `docs/STATUS.md`, and `docs/DECISIONS.md` before changing behavior.

- Preserve the distinction between the deterministic demo and the live LLM/DataHub adapters.
- Never execute generated SQL without the SQL policy and database read-only controls.
- Keep the warehouse reader separate from the audit/control database writer.
- Never log API keys, prompts, question text, result rows, or raw SQL. Audit hashes and bounded metadata instead.
- Update `docs/WORKLOG.md` for each meaningful work session, `docs/BUGS.md` for discovered defects, and `docs/DECISIONS.md` for architectural choices. Add explanations to `docs/LEARNINGS.md`.
- Update `docs/STATUS.md` using observed evidence. Do not call untested integrations or deployment production-verified.
- Run the relevant pytest checks; SQL policy, authentication, execution, and adapter changes require regression coverage. Run the full suite before release.
- Keep real secrets in ignored `.env` files. Use synthetic fixtures in tests and demos.
- Do not publish, spend cloud resources, or change public access without user authorization. Preparing deployment artifacts is authorized.
- Prefer a small modular monolith. New infrastructure needs a recorded problem and decision.

