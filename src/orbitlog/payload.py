"""Minimal payload app used as a fault-injection target.

Mimics an onboard image pipeline: reads an input frame, checks its header and
CRC32, inverts the pixels and writes the result. Logs go to --log. It runs as a
subprocess (`python -m orbitlog.payload ...`), so faults produce real
tracebacks, OS errors and exit codes.

Frame format: b"OLIM" | u16 width | u16 height | u32 crc32(pixels) | pixels (w*h bytes).
"""
import argparse
import logging
import struct
import sys
import zlib

MAGIC = b"OLIM"
HEADER = struct.Struct("<4sHHI")
log = logging.getLogger("payload.imgproc")


def make_frame(width: int, height: int, pixels: bytes) -> bytes:
    assert len(pixels) == width * height
    return HEADER.pack(MAGIC, width, height, zlib.crc32(pixels)) + pixels


class FrameError(ValueError):
    pass


def parse_frame(data: bytes) -> tuple[int, int, bytes]:
    if len(data) < HEADER.size:
        raise FrameError(f"frame too short: {len(data)} bytes < header {HEADER.size}")
    magic, w, h, crc = HEADER.unpack_from(data)
    if magic != MAGIC:
        raise FrameError(f"bad magic {magic!r}")
    pixels = data[HEADER.size:]
    if len(pixels) != w * h:
        raise FrameError(f"truncated pixels: got {len(pixels)}, expected {w * h} ({w}x{h})")
    if zlib.crc32(pixels) != crc:
        raise FrameError(f"crc mismatch: header 0x{crc:08x}, computed 0x{zlib.crc32(pixels):08x}")
    return w, h, pixels


def process(pixels: bytes, fault_stage: str | None) -> bytes:
    if fault_stage == "invert":
        # Injected software fault: index past the end of the pixel buffer.
        return bytes(255 - pixels[i] for i in range(len(pixels) + 1))
    if fault_stage == "stats":
        _ = sum(pixels) / (len(pixels) - len(pixels))  # ZeroDivisionError
    if fault_stage == "metadata":
        meta: dict = {}
        _ = meta["exposure_ms"]  # KeyError
    return bytes(255 - p for p in pixels)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--log", required=True)
    ap.add_argument("--fault-stage", choices=["invert", "stats", "metadata"])
    args = ap.parse_args(argv)
    logging.basicConfig(
        filename=args.log, level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    log.info("start input=%s output=%s", args.input, args.output)
    try:
        with open(args.input, "rb") as f:
            data = f.read()
        w, h, pixels = parse_frame(data)
        log.info("frame ok %dx%d", w, h)
        out = process(pixels, args.fault_stage)
        with open(args.output, "wb") as f:
            f.write(make_frame(w, h, out))
            f.flush()
        log.info("wrote %d bytes", HEADER.size + len(out))
    except Exception:
        log.exception("payload failed")
        raise
    return 0


if __name__ == "__main__":
    sys.exit(main())
