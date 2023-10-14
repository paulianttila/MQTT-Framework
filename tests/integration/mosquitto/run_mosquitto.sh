#!/usr/bin/env bash
mosquitto_passwd -c tests/integration/mosquitto/mosquitto.passwd test-user test-password
cat tests/integration/mosquitto/mosquitto.passwd
mosquitto -c tests/integration/mosquitto/mosquitto.conf -d
