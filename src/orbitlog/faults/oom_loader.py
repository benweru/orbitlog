"""Preprocessing stand-in for oom_alloc_failure. Stdlib only, so it can be
piped into a bare python image:  python oom_loader.py WIDTH HEIGHT CHANNELS

Allocates the decoded frame buffer and writes one byte per 4 KiB page, so the
memory is really resident and a cgroup cap sees it.
"""
import sys


def main() -> None:
    w, h, c = map(int, sys.argv[1:4])
    n = w * h * c
    print(f"preprocess: loading {w}x{h}x{c} frame ({n} bytes)", flush=True)
    buf = bytearray(n)
    buf[::4096] = b"\x01" * len(range(0, n, 4096))
    print("preprocess: frame loaded", flush=True)


if __name__ == "__main__":
    main()
