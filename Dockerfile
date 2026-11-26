# syntax=docker/dockerfile:1
FROM python:3.14-slim

ARG ISIS_REPORT_VERSION=0.15.1
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    HOME=/home/app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates libatomic1 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir "isis-report-lib==${ISIS_REPORT_VERSION}" \
    && python -m playwright install --with-deps chromium \
    && chmod -R a+rX /ms-playwright \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --uid 1000 app \
    && mkdir -p /work \
    && chown app:app /work

USER app
WORKDIR /work

# Build-time smoke test: the runtime user must be able to produce a real PDF.
RUN python -c "from isis_report_lib import generate_pdf; assert generate_pdf({'meta': {'title': 'smoke'}, 'data': [{'x': 1}]}).startswith(b'%PDF')"

ENTRYPOINT ["isis-report"]
CMD ["--help"]
