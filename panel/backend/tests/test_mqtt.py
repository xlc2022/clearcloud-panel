import asyncio

from clearcloud_panel.integrations import mqtt


async def _broker(return_code: int):
    received = {}

    async def handle(reader, writer):
        received["packet"] = await reader.read(256)
        writer.write(bytes([0x20, 0x02, 0x00, return_code]))
        await writer.drain()
        await reader.read(2)
        writer.close()

    server = await asyncio.start_server(handle, "127.0.0.1", 0)
    return server, server.sockets[0].getsockname()[1], received


async def test_connect_accepted():
    server, port, received = await _broker(0)
    async with server:
        result = await mqtt.test(
            {"host": "127.0.0.1", "port": port, "username": "panel"}, {"password": "pw"}
        )
    assert result.ok, result.message
    assert received["packet"][0] == 0x10
    assert b"MQTT" in received["packet"] and b"panel" in received["packet"]


async def test_connect_bad_credentials():
    server, port, _ = await _broker(4)
    async with server:
        result = await mqtt.test({"host": "127.0.0.1", "port": port}, {})
    assert not result.ok
    assert "username or password" in result.message


def test_remaining_length_encoding():
    assert mqtt._remaining_length(0) == b"\x00"
    assert mqtt._remaining_length(127) == b"\x7f"
    assert mqtt._remaining_length(128) == b"\x80\x01"


async def test_unknown_host_reads_plainly():
    result = await mqtt.test({"host": "no-such-host.invalid", "port": 1883}, {})
    assert result.message == "Could not find that host name on the network"


async def test_refused_port_reads_plainly():
    result = await mqtt.test({"host": "127.0.0.1", "port": 9}, {})
    assert result.message == "Nothing is listening at that address and port"
