#!/bin/sh
# Starts Mosquitto with an empty password file if the panel has not written
# one yet, then reloads the broker whenever the panel changes it.
set -eu

PASSWD=/mosquitto/auth/passwd
# The panel container runs as this uid. It replaces the password file by
# writing a temp file and renaming it, so it needs to own the directory.
PANEL_UID=10001

chown "$PANEL_UID" /mosquitto/auth
chmod 0755 /mosquitto/auth

if [ ! -f "$PASSWD" ]; then
  : > "$PASSWD"
fi
chown mosquitto:mosquitto "$PASSWD"
chmod 0600 "$PASSWD"

mosquitto -c /mosquitto/config/mosquitto.conf &
BROKER=$!
trap 'kill -TERM "$BROKER" 2>/dev/null' TERM INT

last=$(stat -c "%i %Y" "$PASSWD")
while kill -0 "$BROKER" 2>/dev/null; do
  sleep 5
  now=$(stat -c "%i %Y" "$PASSWD" 2>/dev/null || echo "$last")
  if [ "$now" != "$last" ]; then
    last=$now
    chown mosquitto:mosquitto "$PASSWD"
    chmod 0600 "$PASSWD"
    kill -HUP "$BROKER"
  fi
done
wait "$BROKER"
