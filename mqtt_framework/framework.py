#!/usr/bin/env python3

import contextlib
import os
import signal
import threading
import logging
from datetime import datetime, timedelta
import time

from flask import Flask as Flask
from flask import jsonify
from cheroot.wsgi import Server as WSGIServer

from flask_mqtt import Mqtt
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from prometheus_flask_exporter import PrometheusMetrics
from prometheus_client import CollectorRegistry, Counter, Summary
import tzlocal

from mqtt_framework.app import App as App, TriggerSource
from mqtt_framework.config import Config as Config

# current MQTT-Framework version
__version__ = "1.1.0"


class ReadOnlyDict(dict):
    def __readonly__(self, *args, **kwargs):
        raise RuntimeError("Read only configuration")

    __setitem__ = __readonly__
    __delitem__ = __readonly__
    pop = __readonly__
    popitem = __readonly__
    clear = __readonly__
    update = __readonly__
    setdefault = __readonly__
    del __readonly__


class Framework:
    def __init__(self):
        self._add_trace_level_to_logger()

        static_folder = Config.WEB_STATIC_DIR
        if os.environ.get("CFG_WEB_STATIC_DIR") is not None:
            static_folder = os.environ.get("CFG_WEB_STATIC_DIR")

        template_folder = Config.WEB_TEMPLATE_DIR
        if os.environ.get("CFG_WEB_TEMPLATE_DIR") is not None:
            template_folder = os.environ.get("CFG_WEB_TEMPLATE_DIR")

        self._flask = Flask(
            __name__, static_folder=static_folder, template_folder=template_folder
        )
        self._mqtt = Mqtt()
        self._scheduler = BackgroundScheduler(timezone=str(tzlocal.get_localzone()))
        self._metrics_registry = CollectorRegistry()
        self._metrics = PrometheusMetrics(self._flask, registry=self._metrics_registry)
        self._mqtt_messages_received_metric = Counter(
            "mqtt_messages_received", "", registry=self._metrics_registry
        )
        self._mqtt_messages_sent_metric = Counter(
            "mqtt_messages_sent", "", registry=self._metrics_registry
        )
        self._do_update_metric = Summary(
            "do_update", "Time spent in do_update", registry=self._metrics_registry
        )
        self._do_update_exception_metric = Counter(
            "do_update_exceptions",
            "How many exceptions caused by do_update",
            registry=self._metrics_registry,
        )
        self._closed = False
        self._limiter = Limiter(
            get_remote_address,
            app=self._flask,
            default_limits=["1 per second"],
            storage_uri="memory://",
            strategy="fixed-window",
        )

        @self._flask.route("/healthy")
        @self._limiter.limit("10 per minute")
        def do_healthy_check():
            if self._app.do_healthy_check():
                self._flask.logger.debug("Healthy check OK")
                return "OK", 200
            else:
                self._flask.logger.warn("Healthy check FAIL")
                return "FAIL", 500

        @self._flask.route("/update")
        @self._limiter.limit("2 per minute")
        def update():
            self._update_now()
            return "OK", 200

        @self._flask.route("/jobs")
        @self._limiter.limit("1 per second")
        def printjobs():
            jobs = []
            for job in self._scheduler.get_jobs():
                jobs.append(
                    {
                        "id": str(job.id),
                        "name": str(job.name),
                        "trigger": str(job.trigger),
                        "next_run": str(job.next_run_time),
                    }
                )
            return jsonify({"jobs": jobs}), 200

        @self._mqtt.on_connect()
        def handle_connect(client, userdata, flags, rc) -> None:
            self._publish_value_to_mqtt_topic("status", "online", True)
            self._subscribe_to_mqtt_topic("updateNow")
            self._subscribe_to_mqtt_topic("setLogLevel")
            try:
                self._app.subscribe_to_mqtt_topics()
            except Exception as e:
                self._flask.logger.exception(f"Error occured: {e}")

        @self._mqtt.on_message()
        def mqtt_message_received(client, userdata, message) -> None:
            self._mqtt_messages_received_metric.inc()
            data = str(message.payload.decode("utf-8"))
            self._flask.logger.debug(
                "MQTT message received: topic=%s, qos=%s, data: %s",
                message.topic,
                str(message.qos),
                data,
            )
            topic = message.topic.removeprefix(self._flask.config["MQTT_TOPIC_PREFIX"])

            if topic == "updateNow" and data.lower() in {"yes", "true", "1"}:
                self._update_now()
            elif topic == "setLogLevel" and data.upper() in {
                "TRACE",
                "DEBUG",
                "INFO",
                "WARNING",
                "ERROR",
                "CRITICAL",
            }:
                self._flask.logger.setLevel(data.upper())
            else:
                try:
                    self._app.mqtt_message_received(topic, data)
                except Exception as e:
                    self._flask.logger.exception(f"Error occured: {e}")

        @self._mqtt.on_log()
        def handle_logging(client, userdata, level, buf) -> None:
            self._flask.logger.trace("MQTT: %s", buf)

    def _to_full_mqtt_topic_name(self, topic: str) -> str:
        return self._flask.config["MQTT_TOPIC_PREFIX"] + topic

    def _subscribe_to_mqtt_topic(self, topic: str) -> None:
        fulltopic = self._to_full_mqtt_topic_name(topic)
        self._flask.logger.debug("Subscribe to MQTT topic: %s", fulltopic)
        self._mqtt.subscribe(fulltopic)

    def _publish_value_to_mqtt_topic(
        self, topic: str, value: str, retain=False
    ) -> None:
        self._mqtt_messages_sent_metric.inc()
        fulltopic = self._to_full_mqtt_topic_name(topic)
        self._flask.logger.debug(
            f"Publish to topic '{fulltopic}' retain {retain}: '{value}'"
        )
        with contextlib.suppress(Exception):
            self._mqtt.publish(fulltopic, value, retain=retain)

    def _start_server(self) -> None:
        self._flask.logger.trace("Start WSGIServer")
        self._WSGIServer = WSGIServer(
            ("0.0.0.0", self._flask.config["WEB_PORT"]), self._flask
        )
        self._WSGIServer.start()  # blocking
        self._flask.logger.trace("WSGIServer stopped")

    def _stop_server(self) -> None:
        self._flask.logger.trace("Stop WSGIServer")
        self._WSGIServer.stop()
        self._server_thread.join()

    def _run_server(self) -> None:
        self._WSGIServer.start()

    def _call_do_update(self, trigger_source: TriggerSource) -> None:
        @self._do_update_metric.time()
        @self._do_update_exception_metric.count_exceptions()
        def do():
            self._app.do_update(trigger_source)

        do()

    def _update_now(self) -> None:
        self._scheduler.remove_all_jobs()
        self._scheduler.add_job(
            self._call_do_update,
            trigger="date",
            args=[TriggerSource.MANUAL],
            id="do_update_manual",
            max_instances=1,
            next_run_time=datetime.now(),
        )
        self.add_scheduler_jobs(
            next_run_time=datetime.now()
            + timedelta(seconds=self._flask.config["UPDATE_INTERVAL"])
        )

    def _signal_handler(self, sig, frame) -> None:
        self._flask.logger.trace("Signal %s received", signal.strsignal(sig))
        self.shutdown()

    def _install_signal_handlers(self) -> None:
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _load_config(self, config: Config) -> None:
        self._flask.config.from_object(config)
        self._flask.config.from_prefixed_env("CFG")

        if self._flask.config["LOG_LEVEL"] in ["TRACE "]:
            logging.getLogger("werkzeug").setLevel(logging.DEBUG)
        else:
            logging.getLogger("werkzeug").setLevel(logging.ERROR)
        self._flask.logger.setLevel(self._flask.config["LOG_LEVEL"])

    def _start_flask(self) -> None:
        self._server_thread = threading.Thread(target=self._start_server)
        self._server_thread.start()

    def _do_wait(self) -> None:
        self._flask.logger.trace("Start blocking")
        while not self._flask.config["EXIT"]:
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                self._flask.logger.trace("KeyboardInterrupt received")
                self.shutdown()
                break

    def _add_trace_level_to_logger(self) -> None:
        TRACE_LOG_LEVEL = 5
        logging.addLevelName(TRACE_LOG_LEVEL, "TRACE")

        def trace(self, message, *args, **kwargs):
            if self.isEnabledFor(TRACE_LOG_LEVEL):
                self._log(TRACE_LOG_LEVEL, message, args, **kwargs)

        logging.Logger.trace = trace

    def add_scheduler_jobs(self, next_run_time) -> None:
        if self._flask.config["UPDATE_INTERVAL"] > 0:
            self._flask.logger.trace(
                "Schedule interval job to happen in every %s sec",
                self._flask.config["UPDATE_INTERVAL"],
            )
            self._scheduler.add_job(
                self._call_do_update,
                name="INTERVAL",
                trigger="interval",
                args=[TriggerSource.INTERVAL],
                id="do_update_interval",
                max_instances=1,
                seconds=self._flask.config["UPDATE_INTERVAL"],
                next_run_time=next_run_time,
            )
        if self._flask.config["UPDATE_CRON_SCHEDULE"]:
            self._flask.logger.trace(
                "Schedule cron job: %s", self._flask.config["UPDATE_CRON_SCHEDULE"]
            )
            self._scheduler.add_job(
                self._call_do_update,
                name="CRON_SCHEDULE",
                trigger=CronTrigger.from_crontab(
                    self._flask.config["UPDATE_CRON_SCHEDULE"]
                ),
                args=[TriggerSource.CRON],
                id="do_update_cron",
                max_instances=1,
            )

    def run(self, app: App, config: Config) -> int:
        return self.start(app, config, blocked=True)

    def start(self, app: App, config: Config, blocked=False) -> int:
        self._load_config(config)

        if blocked:
            self._install_signal_handlers()

        self._app = app
        self._start_flask()
        self._flask.logger.critical(
            "%s version %s started, framework version %s",
            app.__class__.__name__,
            app.get_version(),
            __version__,
        )

        # share some variables and functions to app
        class CallbacksImpl:
            def __init__(self, obj):
                self.obj = obj

            def get_config(self) -> dict:
                return ReadOnlyDict(self.obj._flask.config)

            def get_logger(self) -> logging.Logger:
                return self.obj._flask.logger

            def get_metrics_registry(self) -> CollectorRegistry:
                return self.obj._metrics_registry

            def add_url_rule(
                self,
                rule: str,
                endpoint=None,
                view_func=None,
                provide_automatic_options=None,
                **options,
            ) -> None:
                self.obj._flask.add_url_rule(
                    rule,
                    endpoint=endpoint,
                    view_func=view_func,
                    provide_automatic_options=provide_automatic_options,
                    **options,
                )

            def publish_value_to_mqtt_topic(
                self, topic: str, value: str, retain=False
            ) -> None:
                self.obj._publish_value_to_mqtt_topic(topic, value, retain=retain)

            def subscribe_to_mqtt_topic(self, topic: str) -> None:
                self.obj._subscribe_to_mqtt_topic(topic)

        self._app.init(CallbacksImpl(self))
        self._mqtt.init_app(self._flask)
        self.add_scheduler_jobs(
            next_run_time=datetime.now()
            + timedelta(seconds=self._flask.config["DELAY_BEFORE_FIRST_TRY"])
        )
        self._scheduler.start()
        if blocked:
            self._do_wait()
        return 0

    def _shutdown(self) -> None:
        self._app.stop()
        self._scheduler.shutdown(wait=True)
        self._stop_server()
        self._mqtt.unsubscribe_all()
        self._publish_value_to_mqtt_topic("status", "offline", True)
        self._mqtt._disconnect()

    def shutdown(self) -> None:
        if not self._closed:
            self._closed = True
            self._flask.config["EXIT"] = True
            self._flask.logger.info("Closing...")
            try:
                self._shutdown()
            except Exception as e:
                self._flask.logger.exception(f"Error occured: {e}")
            self._flask.logger.critical("Application stopped")
        else:
            self._flask.logger.trace("Application already stopped")
