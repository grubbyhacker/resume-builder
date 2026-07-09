FROM mcr.microsoft.com/devcontainers/base:ubuntu-24.04

ENV DEBIAN_FRONTEND=noninteractive
ENV MISE_YES=1
ENV UV_PROJECT_ENVIRONMENT=/opt/resume-builder-venv
ENV UV_CACHE_DIR=/opt/uv-cache

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        fonts-liberation \
        git \
        libreoffice-writer \
        make \
        poppler-utils \
        unzip \
    && rm -rf /var/lib/apt/lists/*

RUN curl https://mise.run | sh \
    && mv /root/.local/bin/mise /usr/local/bin/mise

WORKDIR /opt/resume-builder
COPY mise.toml pyproject.toml uv.lock ./
RUN mise trust /opt/resume-builder/mise.toml \
    && mise install \
    && mise exec -- uv sync --locked
