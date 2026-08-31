FROM ghcr.io/astral-sh/uv:0.12.7@sha256:95f2aa1fe59274951cfe9b0cbc7972e879ff1004bc8945d130a32eb0dbd85945 AS uv
FROM python:3.12.13-slim-bookworm@sha256:d50fb7611f86d04a3b0471b46d7557818d88983fc3136726336b2a4c657aa30b

ENV DEBIAN_FRONTEND=noninteractive
ENV MISE_YES=1
ENV UV_PROJECT_ENVIRONMENT=/opt/resume-builder-venv
ENV UV_CACHE_DIR=/opt/uv-cache

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        fontconfig \
        fonts-liberation \
        libreoffice-writer \
        make \
        poppler-utils \
    && rm -rf /var/lib/apt/lists/*

COPY .devcontainer/fontconfig.conf /etc/fonts/conf.d/99-resume-builder.conf
RUN fc-cache -f

COPY --from=uv /uv /uvx /bin/

WORKDIR /opt/resume-builder
COPY mise.toml pyproject.toml uv.lock ./
RUN uv sync --locked --no-install-project
