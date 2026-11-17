# Resume entry

Paste `resume-project.tex` into a Projects section and load `hyperref` in the resume preamble. It uses standard LaTeX rather than assuming a particular resume template.

Public repository: https://github.com/Stark2028/trustsql. The LaTeX entry now uses that real URL. The AWS-hosted edition is a deterministic SQLite/DynamoDB demo; PostgreSQL belongs to the full Docker edition.

The wording describes implemented adapters, SQL-derived lineage, and query-scoped inspection. It keeps the project in progress while live LLM/DataHub checks are pending. The 92 automated tests (full Linux run including PostgreSQL) and 96 expanded synthetic checks are separate measures; neither is model accuracy, a held-out benchmark, or a production SLA. Expanded checks are 32 development scenarios over three seeds, including paraphrases across eight analytics tasks. Update numbers only when verification evidence changes.
