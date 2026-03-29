FROM ubuntu:24.04

ARG DEBIAN_FRONTEND=noninteractive

# Base packages
RUN apt update \
 && apt upgrade -y \
 && apt install -y --no-install-recommends \
   build-essential \
   curl \
   ca-certificates \
   ninja-build \
   cmake \
   git \
   gdb \
   libc-dbg \
   gdbserver \
   python3 \
   python3-pip \
   python-is-python3 \
 && rm -rf /var/lib/apt/lists/*

# Install UV
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/
