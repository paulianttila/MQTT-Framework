# MQTT-Framework

Simple application framework for docker container based MQTT applications.
Purpose of the library is to simplify the application and minimize the boilerplate code.

## Features

* Relaiable MQTT connection and simple data publish and subscribe functionality
* Interval scheduler to e.g. update data to MQTT periodically
* Environment variable based configuration
* REST interface (e.g. /healtcheck)
* Prometheus metrics (/metrics)

## Usage

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
        self.counter = self.counter + 1
        self.publish_value_to_mqtt_topic('counter', self.counter)

if __name__ == '__main__':
    Framework().start(MyApp(), MyConfig(), blocked=True)

```
