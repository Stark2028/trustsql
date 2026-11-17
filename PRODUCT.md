# TrustSQL

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

Python/FastAPI, PostgreSQL, DataHub, OpenAI-compatible LLM connection, Docker. User accepted the proposed architecture and provider/hosting defaults on 2026-11-15. Interface implementation is delegated: same-origin HTML/CSS/JavaScript, avoiding an independent frontend deployment and build chain for this first release.

## Users

An analyst asking questions about a synthetic commerce warehouse; an engineering reviewer inspecting the SQL, retrieved evidence, execution controls, and evaluation results. Initial deployment is a single-owner portfolio application, not a multi-tenant enterprise SaaS.

## Product Purpose

Answer business questions using explicit metadata and show when context is insufficient. Demonstrate whether metadata improves correctness through reproducible evaluation.

## Operating Context

The user is building a DataHub-relevant AI internship project over 1–2 weeks. The supplied one-page DataHub India overview emphasizes metadata/AI context, ingestion/integrations, Python/Java backend engineering, discovery, observability, and governance. This is project inspiration, not an official technical hiring checklist.

## Capabilities and Constraints

- Real SQL execution over synthetic data; integer cents for money.
- Separate deterministic demo and live DataHub/LLM modes; mode must remain visible.
- Metadata retrieval, glossary definitions in dataset context, allowlisted SQL, read-only database execution, bounded results, durable audit records, and a benchmark.
- Model credentials and a reachable DataHub instance are user-supplied. Production hostname/host is undecided.
- Deployment preparation is authorized. A live cloud deployment is not yet selected.
- No fabricated accuracy figures, certification claims, customer logos, or hiring guarantees.

## Product Principles

1. An executable query is not evidence of a correct business answer.
2. Context is evidence, never authority to bypass execution policy.
3. Report uncertainty and incomplete verification explicitly.
4. Keep every result inspectable and every benchmark reproducible.

