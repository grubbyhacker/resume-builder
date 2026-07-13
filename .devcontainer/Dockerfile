FROM mcr.microsoft.com/devcontainers/base:ubuntu-24.04@sha256:d94c97dd9cacf183d0a6fd12a8e87b526e9e928307674ae9c94139139c0c6eae

ENV DEBIAN_FRONTEND=noninteractive
ENV MISE_YES=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        fontconfig \
        fonts-liberation \
        git \
        libreoffice-writer \
        make \
        poppler-utils \
        unzip \
    && rm -rf /var/lib/apt/lists/*

COPY .devcontainer/fontconfig.conf /etc/fonts/conf.d/99-resume-builder.conf
RUN fc-cache -f

RUN curl https://mise.run | sh \
    && mv /root/.local/bin/mise /usr/local/bin/mise
