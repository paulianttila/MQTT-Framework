# MQTT-Framework

Simple application framework for docker container based MQTT applications.
Purpose of the library is to simplify the application and minimize the boilerplate code.

## Features

* Relaiable MQTT connection and simple data publish and subscribe functionality
* Interval and cron scheduler to e.g. update data to MQTT periodically
* Environment variable based configuration
* REST interface (e.g. /healtcheck)
* Prometheus metrics (/metrics)
* Easy logging
* And much more ...

## Environament variables

Following environament varibles are supported by the framework.
Application can extend variables by the configuration.

| **Variable**               | **Default**     | **Descrition**                                                                                                 |
|----------------------------|-----------------|----------------------------------------------------------------------------------------------------------------|
| CFG_APP_NAME               |                 | Name of the app.                                                                                               |
| CFG_LOG_LEVEL              | INFO            | Logging level: CRITICAL, ERROR, WARNING, INFO or DEBUG.                                                        |
| CFG_UPDATE_CRON_SCHEDULE   |                 | Update interval in cron format. Both Unix (5 elements) and Spring (6 elements) formats are supported.          |
| CFG_UPDATE_INTERVAL        | 60              | Update interval in seconds. 0 = disabled                                                                       |
| CFG_DELAY_BEFORE_FIRST_TRY | 5               | Delay before first try in seconds.                                                                             |
| CFG_MQTT_CLIENT_ID         | <CFG_APP_NAME>  | the unique client id string used when connecting to the broker.                                                |
| CFG_MQTT_BROKER_URL        | 127.0.0.1       | MQTT broker URL that should be used for the connection.                                                        |
| CFG_MQTT_BROKER_PORT       | 1883            | MQTT broker port that should be used for the connection.                                                       |
| CFG_MQTT_USERNAME          | None            | MQTT broker username used for authentication. If none is provided authentication is disabled.                  |
| CFG_MQTT_PASSWORD          | None            | MQTT broker password used for authentication.                                                                  |
| CFG_MQTT_TLS_CA_CERTS      | None            | A string path to the Certificate Authority certificate files that are to be treated as trusted by this client. |
| CFG_MQTT_TLS_CERTFILE      | None            | String pointing to the PEM encoded client certificate.                                                         |
| CFG_MQTT_TLS_KEYFILE       | None            | String pointing to the PEM encoded client private key.                                                         |
| CFG_MQTT_TLS_INSECURE      | False           | Configure verification of the server hostname in the server certificate.                                       |
| CFG_MQTT_TOPIC_PREFIX      | <CFG_APP_NAME>/ | MQTT topic prefix.                                                                                             |
| CFG_WEB_STATIC_DIR         | /web/static     | Directory name for static pages.                                                                               |
| CFG_WEB_TEMPLATE_DIR       | /web/templates  | Directory name for templates.                                                                                  |

## MQTT topics

Following MQTT topics are available by default from the framework.

| **Topic**                   | **Descrition**                                                                   |
|-----------------------------|----------------------------------------------------------------------------------|
| < app prefix >/updateNow    | Do immidiate update. Call do_update method from the app.                         |
| < app prefix >/setLogLevel  | Set log level. Supported values: TRACE, DEBUG, INFO, WARNING, ERROR or CRITICAL. |

## Usage

Simple test application (app.py).
See more features from integration test app in tests/integration/testapp folder.

```python
from mqtt_framework import Framework
from mqtt_framework import Config
from mqtt_framework.callbacks import Callbacks
from mqtt_framework.app import TriggerSource

class MyConfig(Config):

    def __init__(self):
        super().__init__(self.APP_NAME)

    APP_NAME = 'test'

    # App specific variables

    TEST_VARIABLE = 123456

class MyApp:

    def init(self, callbacks: Callbacks) -> None:
        self.logger = callbacks.get_logger()
        self.config = callbacks.get_config()
        self.metrics_registry = callbacks.get_metrics_registry()
        self.add_url_rule = callbacks.add_url_rule
        self.publish_value_to_mqtt_topic = callbacks.publish_value_to_mqtt_topic
        self.subscribe_to_mqtt_topic = callbacks.subscribe_to_mqtt_topic
        self.counter = 0

    def get_version(self) -> str:
        return '1.0.0'

    def stop(self) -> None:
        self.logger.debug('Exit')

    def subscribe_to_mqtt_topics(self) -> None:
        self.logger.debug('Subscribe to test topic')
        self.subscribe_to_mqtt_topic('test')

    def mqtt_message_received(self, topic: str, message: str) -> None:
        if topic == 'test':
            self.logger.debug('Received data %s for topic %s', message, topic)

    def do_healthy_check(self) -> bool:
        self.logger.debug('do_healthy_check called')
        return True

    def do_update(self, trigger_source: TriggerSource) -> None:
        self.logger.debug('update called, trigger_source=%s', trigger_source)
        self.logger.debug(f'TEST_VARIABLE from config: {self.config["TEST_VARIABLE"]}')
        self.counter += 1
        self.publish_value_to_mqtt_topic('counter', self.counter)

if __name__ == '__main__':
    Framework().run(MyApp(), MyConfig())

```

### Example Dockerfile

Dockerfile for test app.

```Dockerfile
FROM paulianttila/mqtt-framework:1.1.0

ARG DIR=/app
ARG APP=app.py

ARG USER=app
ARG GROUP=app

ENV DIR=${DIR}
ENV APP=${APP}

COPY requirements.txt /tmp/
RUN pip install --no-cache-dir -r /tmp/requirements.txt && rm /tmp/requirements.txt

RUN mkdir -p ${DIR}
WORKDIR ${DIR}
COPY src ${DIR}

RUN addgroup -S ${GROUP} && adduser -S ${USER} -G ${GROUP}

USER ${USER}
CMD python ${DIR}/${APP}
```

### Example docker-compose.yaml

Docker-compose file for test app.

```yaml
version: "3.5"

services:
  test2mqtt:
    container_name: test2mqtt
    image: <repo>/test2mqtt:1.0.0
    restart: unless-stopped
    environment:
      - CFG_LOG_LEVEL=DEBUG
      - CFG_MQTT_BROKER_URL=<mqtt broker url>
      - CFG_MQTT_BROKER_PORT=1883
      - CFG_TEST_VARIABLE=abcdefg
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/healthy"]
      interval: 60s
      timeout: 3s
      retries: 3
 ```
