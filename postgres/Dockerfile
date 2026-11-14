# Postgres 16 (same Alpine base as before, so existing dev volumes keep their collation)
# plus the pgvector extension for the AI symptom search.
FROM postgres:16.4-alpine

ARG PGVECTOR_VERSION=0.8.0
RUN apk add --no-cache --virtual .pgvector-build git build-base \
    && git clone --branch "v${PGVECTOR_VERSION}" --depth 1 https://github.com/pgvector/pgvector.git /tmp/pgvector \
    && make -C /tmp/pgvector with_llvm=no OPTFLAGS="" \
    && make -C /tmp/pgvector with_llvm=no install \
    && rm -rf /tmp/pgvector \
    && apk del .pgvector-build
