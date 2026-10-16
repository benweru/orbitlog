import socket

from orbitlog.cfs.cmd import (
    APP_NAME_LEN,
    CFE_ES_CMD_MID,
    CFE_ES_RESTART_APP_CC,
    CFE_TBL_CMD_MID,
    CFE_TBL_LOAD_CC,
    CFE_TBL_VALIDATE_CC,
    FAULT_APP_CMD_MID,
    FAULT_APP_EXIT_CC,
    HEADER_LEN,
    PATH_LEN,
    SAMPLE_APP_CMD_MID,
    SAMPLE_APP_NOOP_CC,
    TABLE_NAME_LEN,
    build_command,
    checksum,
    fault_app_exit_cmd,
    load_table_cmd,
    restart_app_cmd,
    sample_noop_cmd,
    send_udp,
    validate_table_cmd,
)


def test_noop_packet_bytes():
    packet = sample_noop_cmd()
    assert packet[:2] == b"\x18\x82"
    assert packet[2:4] == b"\xc0\x00"
    assert packet[4:6] == (HEADER_LEN - 7).to_bytes(2, "big")
    assert packet[6] == SAMPLE_APP_NOOP_CC
    assert len(packet) == HEADER_LEN
    assert checksum(packet[:7] + b"\x00") == packet[7]
    # CFE_MSG_ValidateChecksum treats a packet as valid when ComputeCheckSum
    # returns 0 (the stored byte cancels the 0xFF seed).
    assert checksum(packet) == 0


def test_load_and_validate_sizes_match_the_image():
    loaded = load_table_cmd("/cf/b11.tbl")
    validated = validate_table_cmd()
    restarted = restart_app_cmd("FAULT_APP")
    exited = fault_app_exit_cmd()
    assert len(loaded) == HEADER_LEN + PATH_LEN == 72
    assert len(validated) == HEADER_LEN + 2 + TABLE_NAME_LEN == 50
    assert len(restarted) == HEADER_LEN + APP_NAME_LEN == 28
    assert loaded[0:2] == CFE_TBL_CMD_MID.to_bytes(2, "big")
    assert loaded[6] == CFE_TBL_LOAD_CC
    assert validated[6] == CFE_TBL_VALIDATE_CC
    assert validated[8:10] == b"\x00\x00"
    assert validated[10:22] == b"SAMPLE_APP.E"
    assert restarted[0:2] == CFE_ES_CMD_MID.to_bytes(2, "big")
    assert restarted[6] == CFE_ES_RESTART_APP_CC
    assert exited[0:2] == FAULT_APP_CMD_MID.to_bytes(2, "big")
    assert exited[6] == FAULT_APP_EXIT_CC
    for packet in (loaded, validated, restarted, exited):
        assert checksum(packet) == 0


def test_build_command_rejects_a_wide_function_code():
    try:
        build_command(SAMPLE_APP_CMD_MID, 0x80)
    except ValueError:
        return
    raise AssertionError("expected ValueError")


def test_send_udp_delivers_the_packet():
    packet = sample_noop_cmd()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    try:
        send_udp("127.0.0.1", port, packet)
        data, _ = sock.recvfrom(256)
    finally:
        sock.close()
    assert data == packet
