FROM python:3.11-slim

# Development tools only; no new JARVIS runtime dependency.
RUN python -m pip install --no-cache-dir pytest==9.0.2 ruff==0.15.7 cryptography==46.0.7
COPY entrypoint.py /runner/entrypoint.py
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
ENTRYPOINT ["python", "/runner/entrypoint.py"]
