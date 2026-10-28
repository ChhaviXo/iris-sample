# Assignment-specific PostgreSQL/PostGIS image.
#
# The official postgis/postgis image no longer exposes a 16-3.4 tag. Build
# PostGIS 3.4.6 from its official source archive on a pinned PostgreSQL 16
# base image instead of silently changing the assignment target.

ARG POSTGRES_BASE_IMAGE=postgres:16.15-bookworm@sha256:e8a07d2c7579b038938cdba6c539e580e5001caf9ea203d397b5cc83e76bd938
FROM ${POSTGRES_BASE_IMAGE}

ARG POSTGIS_VERSION=3.4.6
ARG POSTGIS_MD5=eb27b132a2f85650bfa0f4984ffee2e9
ARG POSTGIS_SHA256=294dd4c778a9181be91e4ab305eec53c82ff57a9b7ac7a820fa1a89200436796

RUN set -eux; \
    build_packages=' \
        ca-certificates \
        curl \
        build-essential \
        postgresql-server-dev-16 \
        libpq-dev \
        libgeos-dev \
        libproj-dev \
        libgdal-dev \
        libjson-c-dev \
        libprotobuf-c-dev \
        protobuf-c-compiler \
        libsfcgal-dev \
        libxml2-dev \
        libtool \
        xsltproc \
        libsqlite3-dev \
        libtiff-dev \
        libjpeg-dev \
        libpng-dev \
        libcurl4-gnutls-dev \
        libssl-dev \
        libpcre2-dev \
    '; \
    apt-get update; \
    apt-get install -y --no-install-recommends $build_packages; \
    curl --fail --location --show-error --silent \
        "https://download.osgeo.org/postgis/source/postgis-${POSTGIS_VERSION}.tar.gz" \
        --output "/tmp/postgis-${POSTGIS_VERSION}.tar.gz"; \
    echo "${POSTGIS_MD5}  /tmp/postgis-${POSTGIS_VERSION}.tar.gz" | md5sum --check --strict; \
    echo "${POSTGIS_SHA256}  /tmp/postgis-${POSTGIS_VERSION}.tar.gz" | sha256sum --check --strict; \
    tar --extract --gzip --file "/tmp/postgis-${POSTGIS_VERSION}.tar.gz" --directory /tmp; \
    cd "/tmp/postgis-${POSTGIS_VERSION}"; \
    ./configure --with-pgconfig=/usr/lib/postgresql/16/bin/pg_config; \
    make --jobs="$(nproc)"; \
    make install; \
    ldconfig; \
    cd /; \
    rm -rf "/tmp/postgis-${POSTGIS_VERSION}" "/tmp/postgis-${POSTGIS_VERSION}.tar.gz"; \
    rm -rf /var/lib/apt/lists/*

LABEL org.opencontainers.image.title="IRIS-SIG-40 PostgreSQL/PostGIS" \
      org.opencontainers.image.description="PostgreSQL 16 with PostGIS 3.4.6 for the IRIS-SIG-40 assignment" \
      org.opencontainers.image.version="16.15-postgis-3.4.6"
