# Docker images

## cFS

The `cfs/` image builds the NASA cFS bundle at tag **v7.0.1** (release "cFS Bundle - v7.0.1", published 2026-05-14). The tag is pinned in `docker/cfs/Dockerfile`; the image does not track `main`.

Build and boot:

```
make cfs-build
make cfs-up
```

`make cfs-build` runs `docker build -t orbitlog-cfs docker/cfs`. `make cfs-up` runs that image in the foreground as container `orbitlog-cfs` and removes it on exit, so startup and event messages print on stdout. The same stream is what `docker logs` shows while the container is running. `make cfs-logs` follows those logs. `make cfs-down` removes the container.

`core-cpu1` runs with working directory `/cfs/build-native_std/exe/cpu1`, which is where it finds its startup script and shared objects.

A successful boot prints startup messages and then a line like:

```
CFE_ES_Main: CFE_ES_Main entering OPERATIONAL state
```

The exact wording comes from the boot log in the pull request for this image.

`make cfs-up` passes:

- `--ulimit msgqueue=819200`, so the process is allowed enough POSIX message-queue bytes.
- `--sysctl fs.mqueue.msg_max=256` and `--sysctl fs.mqueue.msgsize_max=16384`. Docker's default `msg_max` is 10. cFS pipe depths are larger than that, and `OS_QueueCreate` then fails with `errno = 22 (Invalid argument)` and `CFE_ES` never reaches OPERATIONAL.

`apps/ci_lab/fsw/inc/ci_lab_internal_cfg.h` is patched before the build so `DEFAULT_CI_LAB_PLATFORM_MAX_INGEST_PKTS` is 64 instead of 10. A `grep -q` right after the `sed` fails the build if the pattern no longer matches.

The image also contains `fault_app.so` and `slow_app.so` (both started from `cfe_es_startup.scr`), the `/opt/orbitlog/burst N [MSGID_HEX [FCN_CODE]]` sender, and bad sample-app tables `/cf/b11.tbl`, `/cf/b42.tbl`, `/cf/b100.tbl` and `/cf/b1000.tbl`. Those are for the fault injectors. `slow_app` owns a depth-4 command pipe (MsgId `0x18B9`) and drains it once every 5 s, so `sb_pipe_full` overflows it with a burst of 9 to 40 commands. `Int1` in each table is the number in the file name, which is above the sample app maximum of 10.

The image runs as root. Even then, the default container lacks `CAP_SYS_NICE`, so startup logs this warning and continues:

```
OS_Posix_TaskAPI_Impl_Init():412:Could not setschedparam in main thread: Operation not permitted (1)
```

Running the same binary as a non-root user produces the same priority warning, because setting realtime priorities is not permitted. It is not a failed boot.
