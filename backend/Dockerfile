FROM python:3.11-slim-bookworm

# Pinned to bookworm specifically (matching .devcontainer/devcontainer.json)
# because the floating `python:3.11-slim` tag can land on a newer Debian
# release where these exact package names have been renamed (e.g.
# libgdk-pixbuf2.0-0), breaking this apt-get install with no code change.

# WeasyPrint needs these native libs for PDF rendering
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 libffi-dev shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
