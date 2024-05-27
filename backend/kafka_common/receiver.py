import logging
import threading
from abc import ABC, abstractmethod
from os import getenv

from confluent_kafka import Consumer


class SingletonMixin:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.__init__(*args, **kwargs)
        return cls._instance


class KafkaReceiver(ABC, SingletonMixin):
    _thread = None
    _topic: str

    def __init__(self):
        self.consumer = Consumer(
            {
                'bootstrap.servers': f'{getenv("KAFKA_HOST")}:{getenv("KAFKA_PORT")}',
                'group.id': 'my-consumer-group',
                'auto.offset.reset': 'earliest',
            }
        )
        self.logger = logging.getLogger(
            name=f'Consumer of topic: {self._topic.upper()}'
        )

    def _consume(self):
        """
        Method to run infinity loop which consumes messages with selected _topic, decode it and then calls custom
        post_consume_action which must be overwritten
        """
        self.consumer.subscribe([self._topic])
        while True:
            message = self.consumer.poll(timeout=1.0)
            if message is None:
                continue
            if message.error():
                logging.error(message.error())
                continue
            msg = message.value().decode('utf-8')
            self.logger.info(f'Got incoming message {msg} with topic: {self._topic}!')

            try:
                self.post_consume_action(msg)
            except Exception as e:
                self.logger.error(
                    f'Could not complete post consume action! {e}', exc_info=True
                )

        self.consumer.close()

    def start_listening(self):
        """Method checks if class already has thread and if it has not then creates thread and starts listening"""
        if self._thread is None or not self._thread.is_alive():
            self._thread = threading.Thread(target=self._consume, daemon=True)
            self._thread.start()
            threading.get_ident()

    @abstractmethod
    def post_consume_action(self, msg: str):
        """Method for handling incoming messages it should be overwritten"""
        raise NotImplementedError
