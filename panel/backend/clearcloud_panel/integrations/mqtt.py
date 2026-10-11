"""MQTT broker check: a bare CONNECT and CONNACK, no client library needed."""

import asyncio
import struct

from .base import Detail, Field, IntegrationType, TestResult, guarded, register

CONNACK_CODES = {
    1: "Broker refused the protocol version",
    2: "Broker refused the client identifier",
    3: "Broker is unavailable",
    4: "Broker rejected the username or password",
    5: "Broker says this client is not authorized",
}


def _string(value: str) -> bytes:
    raw = value.encode()
    return struct.pack("!H", len(raw)) + raw


def _remaining_length(n: int) -> bytes:
    out = bytearray()
    while True:
        byte, n = n % 128, n // 128
        out.append(byte | (0x80 if n else 0))
        if not n:
            return bytes(out)


def connect_packet(client_id: str, username: str | None, password: str | None) -> bytes:
    flags = 0x02  # clean session
    payload = _string(client_id)
    if username:
        flags |= 0x80
        payload += _string(username)
        if password:
            flags |= 0x40
            payload += _string(password)
    variable = _string("MQTT") + bytes([4, flags]) + struct.pack("!H", 30)
    body = variable + payload
    return bytes([0x10]) + _remaining_length(len(body)) + body


@guarded
async def test(config, secrets) -> TestResult:
    host = str(config.get("host") or "").strip()
    port = int(config.get("port") or 1883)
    reader, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout=5)
    try:
        writer.write(
            connect_packet("clearcloud-panel-test", config.get("username"), secrets.get("password"))
        )
        await writer.drain()
        ack = await asyncio.wait_for(reader.readexactly(4), timeout=5)
        writer.write(b"\xe0\x00")  # DISCONNECT
        await writer.drain()
    finally:
        writer.close()
    if ack[0] != 0x20:
        return TestResult.fail("Something answered on that port, but not an MQTT broker")
    if ack[3] != 0:
        return TestResult.fail(
            CONNACK_CODES.get(ack[3], f"Broker refused the connection (code {ack[3]})")
        )
    return TestResult(
        ok=True,
        message="Connected to the MQTT broker",
        details=[Detail(label="Broker", value=f"{host}:{port}")],
    )


TYPE = register(
    IntegrationType(
        kind="mqtt",
        label="MQTT Broker",
        description="Mosquitto in this stack. Blue Iris publishes camera events here.",
        status_key="mqtt",
        fields=[
            Field(key="host", label="Host", type="text", required=True, default="mosquitto"),
            Field(key="port", label="Port", type="number", required=True, default=1883),
            Field(
                key="username",
                label="Username",
                type="text",
                help="Leave blank if the broker allows anonymous clients.",
            ),
            Field(key="password", label="Password", type="secret"),
        ],
        test=test,
    )
)
