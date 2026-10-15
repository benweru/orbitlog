# PLACEHOLDER: NASA cFS build image for fault injection (week 2).
# TODO: pin the cFS bundle by commit (https://github.com/nasa/cFS),
#       build with `make SIMULATION=native prep && make && make install`,
#       and expose EVS/housekeeping output for log capture.
FROM ubuntu:24.04
RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential cmake git ca-certificates && rm -rf /var/lib/apt/lists/*
CMD ["echo", "cFS image not yet implemented"]
