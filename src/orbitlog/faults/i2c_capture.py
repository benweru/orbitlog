"""Camera-capture stand-in for i2c_sensor_nack. Linux only.

    python -m orbitlog.faults.i2c_capture --bus N --addr 0x36 --reg 0x0a

Does one SMBus read-byte-data from the sensor through /dev/i2c-N. A NACK
surfaces as the OSError the kernel returns; it is not caught. i2c-stub only
implements SMBus commands (docs.kernel.org/i2c/i2c-stub.html), so plain
read() is not used. Constants are from include/uapi/linux/i2c-dev.h and
i2c.h; passing the ctypes struct to ioctl is how smbus2 does it.
"""
from __future__ import annotations

import argparse
import ctypes
import os

I2C_SLAVE = 0x0703
I2C_SMBUS = 0x0720
I2C_SMBUS_READ = 1
I2C_SMBUS_BYTE_DATA = 2


class _SmbusData(ctypes.Union):
    _fields_ = [("byte", ctypes.c_uint8), ("word", ctypes.c_uint16), ("block", ctypes.c_uint8 * 34)]


class _SmbusIoctl(ctypes.Structure):
    _fields_ = [("read_write", ctypes.c_uint8), ("command", ctypes.c_uint8),
                ("size", ctypes.c_uint32), ("data", ctypes.POINTER(_SmbusData))]


def read_byte_data(bus: int, addr: int, reg: int) -> int:
    import fcntl

    fd = os.open(f"/dev/i2c-{bus}", os.O_RDWR)
    try:
        fcntl.ioctl(fd, I2C_SLAVE, addr)
        data = _SmbusData()
        msg = _SmbusIoctl(I2C_SMBUS_READ, reg, I2C_SMBUS_BYTE_DATA, ctypes.pointer(data))
        fcntl.ioctl(fd, I2C_SMBUS, msg)
        return data.byte
    finally:
        os.close(fd)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bus", type=int, required=True)
    ap.add_argument("--addr", type=lambda s: int(s, 0), required=True)
    ap.add_argument("--reg", type=lambda s: int(s, 0), required=True)
    a = ap.parse_args(argv)
    print(f"camera: capture start, sensor 0x{a.addr:02x} on i2c-{a.bus}, reg 0x{a.reg:02x}", flush=True)
    value = read_byte_data(a.bus, a.addr, a.reg)
    print(f"camera: sensor id 0x{value:02x}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
