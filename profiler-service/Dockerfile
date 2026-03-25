FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY profiler-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared module
COPY shared /app/shared

# Copy service code
COPY profiler-service/ /app/

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
  CMD python -c "import httpx; httpx.get('http://localhost:8002/health').raise_for_status()"

EXPOSE 8002

CMD ["python", "main.py"]
