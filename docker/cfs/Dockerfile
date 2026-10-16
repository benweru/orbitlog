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

# ci_lab otherwise ingests at most 11 packets per wakeup, and sample_app then
# drains them, so the depth-32 command pipe never overflows.
RUN sed -i 's/DEFAULT_CI_LAB_PLATFORM_MAX_INGEST_PKTS 10/DEFAULT_CI_LAB_PLATFORM_MAX_INGEST_PKTS 64/' \
      apps/ci_lab/fsw/inc/ci_lab_internal_cfg.h \
    && make native_std.prep && make native_std.install

# fault_app is the error-exit target. Bad sample_app tables fail validation
# because Int1 is greater than 10.
COPY fault_app.c bad_table.c burst.c /opt/orbitlog/
RUN set -eux; \
    INC="-I/cfs/sample_defs/inc -I/cfs/build-native_std/inc -I/cfs/build-native_std/native/default_cpu1/inc \
      -I/cfs/cfe/modules/core_api/fsw/inc -I/cfs/cfe/modules/msg/fsw/inc -I/cfs/cfe/modules/tbl/fsw/inc \
      -I/cfs/cfe/modules/es/fsw/inc -I/cfs/cfe/modules/sb/fsw/inc -I/cfs/cfe/modules/evs/fsw/inc \
      -I/cfs/cfe/modules/fs/fsw/inc -I/cfs/cfe/modules/time/fsw/inc -I/cfs/apps/sample_app/fsw/inc \
      -I/cfs/osal/src/os/inc -I/cfs/build-native_std/native/default_cpu1/osal/inc \
      -I/cfs/psp/fsw/inc -I/cfs/build-native_std/native/default_cpu1/psp/inc"; \
    gcc -O2 -o /opt/orbitlog/burst /opt/orbitlog/burst.c; \
    gcc -dM -E $INC /opt/orbitlog/fault_app.c | grep -E 'FAULT_APP_CMD_MID|FAULT_APP_EXIT_CC'; \
    gcc -fPIC -shared $INC -o /cfs/build-native_std/exe/cpu1/cf/fault_app.so /opt/orbitlog/fault_app.c; \
    printf '%s\n' 'CFE_APP, fault_app, FAULT_APP_Main, FAULT_APP, 60, 16384, 0x0, 0;' \
      >> /cfs/build-native_std/exe/cpu1/cf/cfe_es_startup.scr; \
    for n in 11 42 100 1000; do \
      sed "s/{11, 2}/{${n}, 2}/; s/b11.tbl/b${n}.tbl/" \
        /opt/orbitlog/bad_table.c > /tmp/bad_table.c; \
      gcc -c $INC -o /tmp/bad_table.o /tmp/bad_table.c; \
      /cfs/build-native_std/exe/host/elf2cfetbl /tmp/bad_table.o /cfs/build-native_std/exe/cpu1/cf/; \
    done

WORKDIR /cfs/build-native_std/exe/cpu1
CMD ["./core-cpu1"]
