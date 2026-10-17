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

### Known issue

The `dmesg.txt` window is unreliable: it held 0 or 1 lines across seeds, and the count differed between two runs of the
same seeds (a 3-seed print showed seed 2 with the `Virtual chip` line, the later 8-seed run showed it on seeds 1 and 6).
Don't rely on `dmesg.txt` content until the window capture is fixed.

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
