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

The image runs as root. Even then, the default container lacks `CAP_SYS_NICE`, so startup logs this warning and continues:

```
OS_Posix_TaskAPI_Impl_Init():412:Could not setschedparam in main thread: Operation not permitted (1)
```

Running the same binary as a non-root user produces the same priority warning, because setting realtime priorities is not permitted. It is not a failed boot.
