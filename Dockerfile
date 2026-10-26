FROM python:3.15-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV API_HOST=0.0.0.0
ENV API_PORT=8000

RUN useradd -m -u 1000 appuser && mkdir -p /app/invoices && chown -R appuser:appuser /app/invoices

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/live')" || exit 1

USER appuser

CMD ["python", "api_server.py"]
