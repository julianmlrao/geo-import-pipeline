# syntax=docker/dockerfile:1
FROM python:3.12-slim AS build
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /src
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --prefix=/install ".[web]"

FROM python:3.12-slim AS runtime
ENV PYTHONUNBUFFERED=1 \
    GEO_IMPORT_CONFIG_DIR=/app/config/sources \
    GEO_IMPORT_MIGRATIONS=/app/db/migrations \
    GEO_IMPORT_REPORTS_DIR=/app/reports
RUN useradd --system --uid 10001 --create-home app
COPY --from=build /install /usr/local
WORKDIR /app
COPY config ./config
COPY db ./db
COPY data ./data
COPY site/vendor ./site/vendor
RUN mkdir -p /app/reports && chown app /app/reports
USER app
ENTRYPOINT ["geo-import"]
CMD ["schedule"]
