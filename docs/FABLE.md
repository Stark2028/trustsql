# Fable API setup

Prepared 2026-11-17 from the user's provider details and [Fable's documentation](https://fableaiapi.com/docs). This is a third-party provider connection, not direct Anthropic API access.

For this project's OpenAI-compatible adapter, the base URL includes `/v1`:

```dotenv
TRUSTSQL_LLM_BASE_URL=https://api.fableaiapi.com/v1
TRUSTSQL_LLM_MODEL=claude-sonnet-5-5
TRUSTSQL_LLM_API_KEY=
```

Put the real key only in ignored `.env.docker`. Do not paste it into chat, documentation, screenshots, or shell arguments. The existing key field is preserved when preparing provider settings. No paid request was sent during preparation, and the application mode was not changed.

Fable lists model IDs `claude-opus-5-5`, `claude-sonnet-5-5`, and `claude-haiku-5-5`. These are the provider's advertised identifiers. Provider identity/labels are not independent verification of the upstream model.

The provider documents `/v1/chat/completions`, bearer authentication, and tool/function calling. Our current adapter additionally sends `response_format` with strict JSON schema and `max_completion_tokens`. Compatibility of these specific parameters remains unverified. Do not call this integration working until a bounded live request returns a valid typed plan. If those parameters are unsupported, adapt the request to the provider's confirmed protocol while keeping local plan validation and SQL/database controls.

Leave demo mode enabled until the provider connection is tested. Full app live mode also requires reachable DataHub metadata; configuring the model alone does not complete that dependency. A single provider smoke request can be tested independently before a larger paid evaluation is authorized.

## First live attempt — 2026-11-17

After the user confirmed the key was added, sent one synthetic request through the existing adapter. Observed HTTP 200 followed by Pydantic `ValidationError` when decoding the query plan. No warehouse query was executed and the app mode was unchanged. This does not establish whether the cause is unsupported strict schema, invalid JSON/schema fields, or another response-format issue. Raw response text was not printed or persisted. Do not claim the provider integration is working from HTTP status alone.

`scripts/check_provider.py --send` performs one explicit paid test and prints only redacted status metadata. It has no automatic retries, does not switch app mode, and does not launch the full evaluation. Future diagnostics also report standard validation error types without rejected inputs or raw model output.
