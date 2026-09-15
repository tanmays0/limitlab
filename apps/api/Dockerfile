FROM python:3.12-slim

WORKDIR /app

COPY packages/limiter /tmp/limiter
COPY apps/api /app

RUN pip install --no-cache-dir /tmp/limiter \
    && pip install --no-cache-dir \
      "fastapi>=0.115.0" \
      "uvicorn[standard]>=0.30.0" \
      "pydantic-settings>=2.4.0" \
      "redis>=5.0.0" \
      "httpx>=0.27.0"

ENV PYTHONPATH=/app
ENV API_HOST=0.0.0.0
ENV API_PORT=8080

EXPOSE 8080

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
