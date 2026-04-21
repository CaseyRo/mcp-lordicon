FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1

COPY pyproject.toml README.md ./
COPY mcp_lordicon/ ./mcp_lordicon/

# Bake the git commit into the image so /health/detail can report it.
# Known limitation: Komodo git-deploy does not forward --build-arg, so under
# normal Komodo deploys this value will be "unknown". See Standards §13.
ARG GIT_COMMIT=unknown
RUN echo "${GIT_COMMIT}" > /app/.git_commit

RUN pip install --no-cache-dir . \
    && addgroup --system mcp && adduser --system --ingroup mcp mcp

USER mcp

ENV TRANSPORT=http
ENV HOST=0.0.0.0

EXPOSE 8000

# Healthcheck hits the public /health so Docker doesn't need a bearer token.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python3 -c "from urllib.request import urlopen;import json;r=urlopen('http://localhost:8000/health');d=json.loads(r.read());exit(0 if d.get('status')=='healthy' else 1)"

CMD ["mcp-lordicon"]
