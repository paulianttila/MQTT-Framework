""" Base configuration """

import ssl


class Config(object):

    EXIT = False
    LOG_LEVEL = "INFO"
    UPDATE_INTERVAL = 60
    DELAY_BEFORE_FIRST_TRY = 5
    UPDATE_CRON_SCHEDULE = None
    WEB_PORT = 5000
    WEB_STATIC_DIR = "/web/static"
    WEB_TEMPLATE_DIR = "/web/templates"

    MQTT_BROKER_URL = "127.0.0.1"
    MQTT_BROKER_PORT = 1883
    MQTT_USERNAME = ""
    MQTT_PASSWORD = ""
    MQTT_KEEPALIVE = 30
    MQTT_TLS_ENABLED = False
    MQTT_TLS_CA_CERTS = None
    MQTT_TLS_CERTFILE = None
    MQTT_TLS_KEYFILE = None
    MQTT_TLS_VERSION = ssl.PROTOCOL_TLSv1_2
    MQTT_TLS_INSECURE = False
    MQTT_LAST_WILL_MESSAGE = "offline"
    MQTT_LAST_WILL_RETAIN = True

    def __init__(self, app_name: str):
        self.app_name = app_name

    @property
    def MQTT_CLIENT_ID(self):
        return f"{self.app_name}"

    @property
    def MQTT_TOPIC_PREFIX(self):
        return f"{self.app_name}/"

    @property
    def MQTT_LAST_WILL_TOPIC(self):
        return f"{self.app_name}/status"
