import stat

from clearcloud_panel.crypto import SecretBox, load_or_create_key


def test_key_is_created_private_and_reused(tmp_path):
    path = tmp_path / "k" / "panel.key"
    key = load_or_create_key(path)
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert load_or_create_key(path) == key


def test_seal_round_trip_hides_plaintext(tmp_path):
    box = SecretBox(load_or_create_key(tmp_path / "panel.key"))
    blob = box.seal({"token": "s3cret-value"})
    assert b"s3cret-value" not in blob
    assert box.open(blob) == {"token": "s3cret-value"}
    assert box.open(None) == {}
