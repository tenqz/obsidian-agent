FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN pip install --no-cache-dir mcp uvicorn

COPY . .

EXPOSE 8001

CMD ["python", "-m", "app.mcp.server"]
