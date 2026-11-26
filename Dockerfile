# syntax=docker/dockerfile:1@sha256:572cebbc2b15e6f84c077742952674889cb63cd5e9b80abdffcbe587b6f19183
FROM python:3.14-slim@sha256:22eafb370920ad8b429e0aec3fff433e0669968519f5d60469d83729c138b28b

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    HOME=/home/app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates libatomic1 \
    && rm -rf /var/lib/apt/lists/*

COPY docker/requirements.txt /tmp/requirements.txt

RUN pip install --no-cache-dir --require-hashes -r /tmp/requirements.txt \
    && python -m playwright install --with-deps chromium \
    && chmod -R a+rX /ms-playwright \
    && rm -rf /var/lib/apt/lists/* /tmp/requirements.txt

RUN useradd --create-home --uid 1000 app \
    && mkdir -p /work \
    && chown app:app /work

USER app
WORKDIR /work

# Build-time smoke test: the runtime user must be able to produce a real PDF.
RUN python -c "from isis_report_lib import generate_pdf; assert generate_pdf({'meta': {'title': 'smoke'}, 'data': [{'x': 1}]}).startswith(b'%PDF')"

ENTRYPOINT ["isis-report"]
CMD ["--help"]
