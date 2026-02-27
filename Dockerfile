FROM debian:12-slim

ARG DEBIAN_FRONTEND=noninteractive
# Pin package resolution to a Debian snapshot for reproducibility.
ARG APT_SNAPSHOT=20250115T000000Z

RUN set -eux; \
    printf 'deb [check-valid-until=no] http://snapshot.debian.org/archive/debian/%s/ bookworm main\n' "$APT_SNAPSHOT" > /etc/apt/sources.list; \
    printf 'deb [check-valid-until=no] http://snapshot.debian.org/archive/debian-security/%s/ bookworm-security main\n' "$APT_SNAPSHOT" >> /etc/apt/sources.list; \
    apt-get -o Acquire::Check-Valid-Until=false update; \
    apt-get install -y --no-install-recommends \
      bash \
      ca-certificates \
      coreutils \
      git \
      jq \
      make \
      python3 \
      python3-pip \
      python3-venv \
      sby \
      yosys \
      z3 \
      boolector; \
    rm -rf /var/lib/apt/lists/*

RUN useradd -m -u 1000 app
USER app
WORKDIR /workspace

COPY . /workspace

RUN python3 -m pip install --user --upgrade pip && \
    python3 -m pip install --user -e .

RUN /workspace/scripts/print-tool-versions.sh > /workspace/.formal-tool-versions.txt

ENV PATH="/home/app/.local/bin:${PATH}"

CMD ["bash"]
