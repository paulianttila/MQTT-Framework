#!/usr/bin/env bash

# exit when any command fails
set -e

PWD=$(pwd)

# set configuration for test app
export CFG_MQTT_BROKER_URL=localhost
export CFG_MQTT_BROKER_PORT=1883
export CFG_WEB_STATIC_DIR=${PWD}/example/web/static
export CFG_WEB_TEMPLATE_DIR=${PWD}/example/web/templates
export CFG_WEB_PORT=8080
export CFG_LOG_LEVEL=DEBUG
export CFG_UPDATE_INTERVAL=1
export CFG_DELAY_BEFORE_FIRST_TRY=1

TEST_APP_PID=

start_test_app() {
  # start the test app whch use framework
  echo "Start test app"
  cd example
  python main.py &
  TEST_APP_PID=$!
  echo "PID=${TEST_APP_PID}"
  jobs
  cd ..
}

run_tests() {
  # add testing_utils.py to tavern tests
  export PYTHONPATH=${PYTHONPATH}:/${PWD}/tests/integration/
  env
  # run tests
  python -m pytest tests/
}

clean_up() {
  echo "Stop test app, PID=${TEST_APP_PID}"
  kill ${TEST_APP_PID}
}

pwd
ls -lR

start_test_app
run_tests
clean_up
