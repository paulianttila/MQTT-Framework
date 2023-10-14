#!/usr/bin/env bash
mosquitto_passwd -b tests/integration/mosquitto/mosquitto.passwd testuser testpassword
mosquitto -c tests/integration/mosquitto/mosquitto.conf -d
