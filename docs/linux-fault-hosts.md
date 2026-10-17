# Running the Linux-only faults on a Windows laptop (WSL2)

Two fault classes need things Docker Desktop's VM and Windows-side Python don't have:

| Class | Needs | Default |
|---|---|---|
| `disk_full` | `/dev/full` on the host running Python | registered |
| `i2c_sensor_nack` | Linux, root, the `i2c-stub` and `i2c-dev` kernel modules | opt-in: `ORBITLOG_ENABLE_I2C_STUB=1` |

Run these from a WSL2 Ubuntu shell, not from Windows. On Windows, `disk_full` records `trigger_status: failed`
(no `/dev/full`) and `i2c_sensor_nack` is not registered.

## Evidence (17 Oct 2026)

Host fingerprint: `Linux Benweru 6.6.87.2-microsoft-standard-WSL2 #1 SMP PREEMPT_DYNAMIC Thu Jun 5 18:30:46 UTC 2025 x86_64`
(Windows 11 Pro build 26200, Intel Core Ultra 7 155H, Ubuntu 24.04.3 in WSL2, Docker Desktop 29.8.0). Repo at `a9b93f6`.

**`make dataset N=30 SEED=0` in WSL2** with a running cFS container:

```
cases: 30
by fault_class: cfs_app_crash_restart=5, corrupt_input_file=5, disk_full=4, oom_alloc_failure=4, payload_python_exception=4, sb_pipe_full=4, table_load_validation=4
by trigger_status: triggered=30
by capture: captured=30
```

On Windows the same command left all 5 `disk_full` cases `failed`. In WSL2 the `disk_full` cases contain
`OSError: [Errno 28] No space left on device`.

**`i2c_sensor_nack`, 8 seeds, as root with `ORBITLOG_ENABLE_I2C_STUB=1`:**

```
seed 0: triggered | OSError: [Errno 19] No such device | dmesg lines=0
seed 1: triggered | OSError: [Errno 19] No such device | dmesg lines=1
seed 2: triggered | OSError: [Errno 19] No such device | dmesg lines=0
seed 3: triggered | OSError: [Errno 19] No such device | dmesg lines=0
seed 4: triggered | OSError: [Errno 19] No such device | dmesg lines=0
seed 5: triggered | OSError: [Errno 19] No such device | dmesg lines=0
seed 6: triggered | OSError: [Errno 19] No such device | dmesg lines=1
seed 7: triggered | OSError: [Errno 19] No such device | dmesg lines=0
```

`pytest -m linux_i2c` passed (`1 passed, 85 deselected`).

### How this differs from the Satlyt article

The article shows `tegra-i2c 3180000.i2c: no acknowledge from address 0x36` and `OSError: [Errno 121] Remote I/O error`.
`i2c-stub` is a software SMBus emulator. For an address with no emulated chip it returns **Errno 19 (ENODEV)**, and it
prints no "no acknowledge" kernel warning. The only kernel line it can add is `i2c-stub: Virtual chip at 0x..`.
So this class reproduces the shape of the fault (a sensor read fails, `OSError` in the payload) but **not** the
tegra signature. Dataset consumers and any model evaluation must treat it as an Errno 19 variant.
A real NACK (Errno 121 plus the kernel warning) needs a real controller driver and isn't available on a generic
Linux host.

### `dmesg.txt` window (fixed, 17 Oct 2026)

The first runs above had a `dmesg.txt` that held 0 or 1 lines and differed between runs of the same seeds. The window was
cut by line count, but the kernel log is a fixed-size ring buffer (256 KiB here): when it is full, old lines are evicted
as new ones arrive and a count slice drops lines. A WSL2 VM shares one log with Docker Desktop, so it fills in a long
session. The window is now cut by the `[seconds.microseconds]` timestamp (`dmesg_new_lines` in `faults/linux.py`).

With the ring full and test noise written to `/dev/kmsg` while the fault runs, 8 seeds gave:

```
old code: seeds missing the 'Virtual chip' line = 8 of 8   (dmesg_lines: 2,2,2,1,2,2,2,2)
new code: seeds missing the 'Virtual chip' line = 0 of 8   (dmesg_lines: 12,11,10,11,12,11,11,11)
```

The window is a time slice, so it also holds any unrelated kernel line logged during the trigger (the extra lines in the
new-code run are the test noise).

## Building `i2c-stub` for the WSL2 kernel (no reboot, no admin)

The stock WSL2 kernel has `CONFIG_I2C=y` and `CONFIG_I2C_CHARDEV=m` but no `CONFIG_I2C_STUB`. Build the two modules
against the exact running kernel and load them. The kernel image and `.wslconfig` are not changed.

In the WSL Ubuntu shell, as root (`wsl -d Ubuntu -u root` from Windows needs no password):

```bash
apt-get install -y build-essential flex bison libssl-dev libelf-dev bc dwarves git cpio
git clone --depth 1 --branch linux-msft-wsl-$(uname -r | cut -d- -f1) https://github.com/microsoft/WSL2-Linux-Kernel.git
cd WSL2-Linux-Kernel
zcat /proc/config.gz > .config
scripts/config --module I2C_STUB && make olddefconfig
# LOCALVERSION= (set, empty) stops the build appending "+", so the modules match `uname -r`
make -j"$(nproc)" LOCALVERSION= modules          # full build, roughly 20 to 30 minutes on 22 threads
mkdir -p /lib/modules/$(uname -r)/extra
cp drivers/i2c/i2c-stub.ko drivers/i2c/i2c-dev.ko /lib/modules/$(uname -r)/extra/ && depmod -a
modinfo drivers/i2c/i2c-stub.ko | grep vermagic   # must start with the output of: uname -r
```

**Repeat the `mkdir`/`cp`/`depmod` lines after every WSL restart** (`wsl --shutdown`, a reboot, or an idle stop). On start
WSL mounts its own modules disk over `/lib/modules/<kernel>`, which hides the copied `i2c-*.ko`; `modprobe` then reports
`Module i2c-stub not found`. The built files stay in `WSL2-Linux-Kernel/drivers/i2c/`, so only the copy is needed again
(no rebuild). Found 17 Oct 2026, after the VM restarted overnight.

The modules are needed in full because `CONFIG_MODVERSIONS=y` requires the symbol checksums from a complete build.
The `BPF: Invalid name_offset` / `BTF mismatch` messages when loading only affect debug info. Don't load the modules
by hand before running the test: the injector refuses to run if `i2c-stub` is already loaded.

Run the live test:

```bash
sudo ORBITLOG_ENABLE_I2C_STUB=1 .venv/bin/python -m pytest -m linux_i2c -v
```

`sudo` drops the environment variable unless you pass it as above.

### Dataset from WSL2 with Docker Desktop

If Docker Desktop's WSL integration is off for your distro, put a shim on `PATH` that calls the Windows binary:

```sh
#!/bin/sh
exec "/mnt/c/Program Files/Docker/Docker/resources/bin/docker.exe" "$@"
```

The dataset code only uses `docker run/exec/logs/port/inspect`, with no bind mounts, so the shim is enough.
Start the cFS container with the same flags as `make cfs-up` plus `-p 127.0.0.1::1234/udp`, then `make dataset N=30 SEED=0`.
