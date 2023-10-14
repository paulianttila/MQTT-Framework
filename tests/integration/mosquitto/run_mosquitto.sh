#!/usr/bin/env bash
echo "Set password for testuser"
mosquitto_passwd -b tests/integration/mosquitto/mosquitto.passwd testuser testpassword
echo "Run mosquitto"
mosquitto -c tests/integration/mosquitto/mosquitto.conf &
