# Code interpreter for hosts without a Docker socket (Railway).
# The scientific executor image provides the interpreter that runs the
# snippets; the code-interpreter API comes from its own release, plus a
# "local" executor backend that runs snippets as child processes.
FROM onyxdotapp/code-interpreter:0.4.7 AS api

FROM onyxdotapp/python-executor-sci@sha256:94dda93e6cb56847cfc5a250db0519eb2972def88791e85aeef04989906bb4bf

COPY --from=api /app /app
COPY executor_local.py /app/app/services/executor_local.py
RUN python3 - <<'EOF'
from pathlib import Path

factory = Path("/app/app/services/executor_factory.py")
source = factory.read_text()
marker = '    else:\n        raise ValueError(f"Unknown executor backend: {backend}")'
assert marker in source
factory.write_text(
    source.replace(
        marker,
        '    elif backend == "local":\n'
        "        from app.services.executor_local import LocalExecutor\n\n"
        "        return LocalExecutor()\n" + marker,
    )
)
EOF

WORKDIR /app
ENV PATH=/app/.venv/bin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
    EXECUTOR_BACKEND=local \
    LOCAL_EXECUTOR_PYTHON=/opt/executor-venv/bin/python \
    MEMORY_LIMIT_MB=1024 \
    CPU_TIME_LIMIT_SEC=30
ENTRYPOINT []
CMD ["code-interpreter-api"]
