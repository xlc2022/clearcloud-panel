from .base import Field

VERIFY_TLS = Field(
    key="verify_tls",
    label="Verify TLS Certificate",
    type="bool",
    default=False,
    help="Leave off for the self-signed certificate the device ships with.",
)
