FROM python:3.12-slim@sha256:5e2bdb1b0d542d5039cffb8181c65930093949194a65c365dfb1b0fe13a4fa5b AS builder
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_DEFAULT_TIMEOUT=120 PIP_RETRIES=3
WORKDIR /build
COPY requirements.lock ./
RUN --mount=type=cache,target=/root/.cache/pip pip wheel --wheel-dir /wheels -r requirements.lock
COPY pyproject.toml README.md ./
COPY src ./src
RUN --mount=type=cache,target=/root/.cache/pip pip wheel --no-deps --wheel-dir /wheels .

FROM builder AS checks
RUN pip install --no-index --find-links=/wheels trustsql && pip install pytest==9.1.1
WORKDIR /checks
COPY tests ./tests
COPY scripts ./scripts
ENV PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
CMD ["python", "-m", "pytest", "-q", "-p", "no:cacheprovider"]

FROM python:3.12-slim@sha256:5e2bdb1b0d542d5039cffb8181c65930093949194a65c365dfb1b0fe13a4fa5b AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN groupadd --gid 10001 trustsql && useradd --uid 10001 --gid trustsql --create-home trustsql
WORKDIR /app
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir --no-index --find-links=/wheels trustsql && rm -rf /wheels
COPY --chown=trustsql:trustsql scripts/healthcheck.py /app/healthcheck.py
RUN mkdir /app/var && chown trustsql:trustsql /app/var
USER 10001:10001
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 CMD ["python", "/app/healthcheck.py"]
CMD ["python", "-m", "uvicorn", "trustsql.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--no-access-log", "--no-proxy-headers", "--limit-concurrency", "32", "--timeout-keep-alive", "5"]

