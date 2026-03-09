FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
ENV IS_SANDBOX=1

RUN apt-get update && apt-get install -y \
    git \
    gh \
    curl \
    wget \
    unzip \
    fish \
    python3 \
    ca-certificates \
    gnupg \
    direnv \
    nano \
    jq \
    && rm -rf /var/lib/apt/lists/*

# Node.js 22 LTS via nodesource
RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# install agent browser
RUN npx playwright install-deps
RUN npm install -g agent-browser
# npx --yes agent-browser install --with-deps
RUN agent-browser install
RUN agent-browser install --with-deps

# Claude Code (native install)
RUN curl -fsSL https://claude.ai/install.sh | bash
# Other AI coding tools
RUN npm install -g @openai/codex \
    && curl -fsSL https://opencode.ai/install | bash

# Go and ralphex
RUN ARCH=$(dpkg --print-architecture) && \
    if [ "$ARCH" = "arm64" ]; then GOARCH="arm64"; else GOARCH="amd64"; fi && \
    curl -fsSL https://go.dev/dl/go1.26.0.linux-${GOARCH}.tar.gz | tar -C /usr/local -xz
ENV GOROOT=/usr/local/go
ENV GOPATH=/root/go
ENV PATH="${GOROOT}/bin:${GOPATH}/bin:${PATH}"
RUN go install github.com/umputun/ralphex/cmd/ralphex@latest

# Starship prompt
RUN curl -fsSL https://starship.rs/install.sh | sh -s -- -y

# Add CLI tools to PATH
ENV PATH="/root/.claude/bin:/root/.opencode/bin:${PATH}"

# Set fish as default shell
RUN chsh -s /usr/bin/fish

CMD ["fish"]
