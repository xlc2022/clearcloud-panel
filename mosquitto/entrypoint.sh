#!/bin/sh
# Starts Mosquitto with an empty password file if the panel has not written
# one yet, then reloads the broker whenever the panel changes it.
set -eu

PASSWD=/mosquitto/auth/passwd

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
