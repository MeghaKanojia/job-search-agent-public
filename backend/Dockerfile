FROM python:3.11-slim-bookworm

# Exact package list per WeasyPrint's own current docs for Debian >= 11 with
# prebuilt wheels (https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#debian-ubuntu):
# libpango-1.0-0, libpangoft2-1.0-0, libharfbuzz-subset0. Earlier versions of
# this file installed a broader, outdated set (libpangocairo-1.0-0,
# libgdk-pixbuf2.0-0, libffi-dev, shared-mime-info) that happened to work in
# the bookworm-based Codespace but broke a Render build with "Package
# 'libgdk-pixbuf2.0-0' has no installation candidate" -- that package isn't
# actually required by current WeasyPrint at all.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
