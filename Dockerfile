# syntax=docker/dockerfile:1
FROM python:3.14-slim

ARG ISIS_REPORT_VERSION=0.15.1
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates libatomic1 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir "isis-report-lib==${ISIS_REPORT_VERSION}" \
    && python -m playwright install --with-deps chromium \
    && rm -rf /var/lib/apt/lists/*

# Build-time smoke test: the image must be able to produce a real PDF.
RUN python -c "from isis_report_lib import generate_pdf; assert generate_pdf({'meta': {'title': 'smoke'}, 'data': [{'x': 1}]}).startswith(b'%PDF')"

WORKDIR /work
ENTRYPOINT ["isis-report"]
CMD ["--help"]
