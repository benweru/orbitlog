# NASA cFS bundle pinned to tag v7.0.1 (published 2026-05-14).
# Build: make native_std.prep && make native_std.install
# Run from build-native_std/exe/cpu1 so core-cpu1 finds its startup script and shared objects.
FROM ubuntu:24.04

RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential cmake git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /cfs
RUN git clone --branch v7.0.1 --depth 1 https://github.com/nasa/cFS.git . \
    && (git submodule update --init --depth 1 || git submodule update --init)

RUN make native_std.prep && make native_std.install

WORKDIR /cfs/build-native_std/exe/cpu1
CMD ["./core-cpu1"]
