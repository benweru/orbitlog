"""CCSDS command packets for the cFS v7.0.1 non-EDS build.

Numbers below were read from the orbitlog-cfs image (nasa/cFS tag v7.0.1,
EDS disabled). A probe compiled against
build-native_std/native/default_cpu1/inc printed:

    sizeof header 8
    sizeof load 72
    sizeof validate 50
    sizeof restart 28
    LOAD_CC 2 VALIDATE_CC 4
    RESTART_CC 6 STOP_CC 5
    SAMPLE_NOOP 0
    TBL_MID 0x1804 ES_MID 0x1806 SAMPLE_MID 0x1882

Those match default_cfe_*_fcncode_values.h, default_*_topicids.h and
default_cfe_core_api_msgid_mapping.h (command base 0x1800). Payload sizes
match CFE_MISSION_MAX_PATH_LEN 64, CFE_MISSION_TBL_MAX_FULL_NAME_LEN 40 and
CFE_MISSION_MAX_API_LEN 20. The checksum is CFE_MSG_ComputeCheckSum: 0xFF
XOR of every byte, with the checksum byte zero while it is computed.
"""
from __future__ import annotations

import socket

HEADER_LEN = 8
PATH_LEN = 64
TABLE_NAME_LEN = 40
APP_NAME_LEN = 20

CFE_TBL_CMD_MID = 0x1804
CFE_ES_CMD_MID = 0x1806
SAMPLE_APP_CMD_MID = 0x1882
# Topic 0xB7 is unused in the v7.0.1 bundle. The image build prints this
# macro from fault_app.c via gcc -dM.
FAULT_APP_CMD_MID = 0x18B7

CFE_TBL_LOAD_CC = 2
CFE_TBL_VALIDATE_CC = 4
CFE_ES_RESTART_APP_CC = 6
SAMPLE_APP_NOOP_CC = 0
FAULT_APP_EXIT_CC = 1

TABLE_NAME = "SAMPLE_APP.ExampleTable"
SAMPLE_PIPE_DEPTH = 32


def checksum(packet: bytes) -> int:
    """Return the cFS command checksum for a packet whose checksum byte is 0."""
    value = 0xFF
    for byte in packet:
        value ^= byte
    return value & 0xFF


def build_command(msg_id: int, function_code: int, payload: bytes = b"") -> bytes:
    """Build one command packet. msg_id is the CCSDS stream id (big endian)."""
    if not 0 <= msg_id <= 0xFFFF:
        raise ValueError(f"msg_id out of range: {msg_id}")
    if not 0 <= function_code <= 0x7F:
        raise ValueError(f"function code out of range: {function_code}")
    total = HEADER_LEN + len(payload)
    packet = bytearray(total)
    packet[0] = (msg_id >> 8) & 0xFF
    packet[1] = msg_id & 0xFF
    packet[2] = 0xC0  # unsegmented, sequence 0
    packet[3] = 0x00
    ccsds_length = total - 7
    packet[4] = (ccsds_length >> 8) & 0xFF
    packet[5] = ccsds_length & 0xFF
    packet[6] = function_code
    packet[7] = 0
    packet[HEADER_LEN:] = payload
    packet[7] = checksum(packet)
    return bytes(packet)


def _fixed(text: str, size: int) -> bytes:
    raw = text.encode("ascii")
    if len(raw) >= size:
        raise ValueError(f"{text!r} does not fit in {size} bytes")
    return raw + b"\x00" * (size - len(raw))


def load_table_cmd(filename: str) -> bytes:
    """CFE_TBL_LOAD_CC. Filename only; the table name is inside the .tbl file."""
    return build_command(CFE_TBL_CMD_MID, CFE_TBL_LOAD_CC, _fixed(filename, PATH_LEN))


def validate_table_cmd(table_name: str = TABLE_NAME, inactive: bool = True) -> bytes:
    """CFE_TBL_VALIDATE_CC. ActiveTableFlag is a little-endian uint16 on this image."""
    flag = (0 if inactive else 1).to_bytes(2, "little")
    return build_command(CFE_TBL_CMD_MID, CFE_TBL_VALIDATE_CC, flag + _fixed(table_name, TABLE_NAME_LEN))


def restart_app_cmd(app_name: str) -> bytes:
    return build_command(CFE_ES_CMD_MID, CFE_ES_RESTART_APP_CC, _fixed(app_name, APP_NAME_LEN))


def sample_noop_cmd() -> bytes:
    return build_command(SAMPLE_APP_CMD_MID, SAMPLE_APP_NOOP_CC)


def fault_app_exit_cmd() -> bytes:
    return build_command(FAULT_APP_CMD_MID, FAULT_APP_EXIT_CC)


def send_udp(host: str, port: int, packet: bytes) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.sendto(packet, (host, port))
