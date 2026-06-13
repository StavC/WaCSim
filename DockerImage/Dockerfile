FROM ubuntu:22.04

# Prevent interactive prompts during installation
ENV DEBIAN_FRONTEND=noninteractive

# Install core packages and network emulation utilities
RUN apt-get update && apt-get install -y \
    git \
    python3 \
    python3-pip \
    curl \
    sudo \
    lsb-release \
    iptables \
    iproute2 \
    net-tools \
    tcpdump \
    openvswitch-switch \
    libnfnetlink-dev \
    libnetfilter-queue-dev \
    && rm -rf /var/lib/apt/lists/*

# Install cpppo
RUN python3 -m pip install cpppo

# Clone and install custom MiniCPS
RUN git clone --depth 1 https://github.com/StavC/minicps.git /tmp/minicps \
    && cd /tmp/minicps \
    && python3 -m pip install . \
    && rm -rf /tmp/minicps

# Clone and install custom epynet wrapper
RUN git clone --depth 1 https://github.com/StavC/DHALSIM-epynet.git /tmp/epynet \
    && cd /tmp/epynet \
    && python3 -m pip install . \
    && rm -rf /tmp/epynet

# Clone and install Mininet
RUN apt-get update && git clone --depth 1 https://github.com/StavC/mininet.git /tmp/mininet \
    && cd /tmp/mininet \
    && PYTHON=python3 ./util/install.sh -fnv \
    && rm -rf /tmp/mininet \
    && rm -rf /var/lib/apt/lists/*

# Install custom netfilterqueue
RUN python3 -m pip install -U git+https://github.com/StavC/python-netfilterqueue

# Copy WaCSim codebase and install it
WORKDIR /wacsim
COPY . /wacsim
RUN python3 -m pip install -e .

# Set up the entrypoint to boot Open vSwitch
COPY DockerImage/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
CMD ["bash"]
