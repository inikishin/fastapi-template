from logging import Formatter, StreamHandler, Logger, INFO


class LoggerProvider:
    """
    Вспомогательный класс для получения логера. Применяет базовые настройки к
    встроенному логеру и возвращает инстанс логера с указанным названием.
    """

    def __init__(self):
        linear_formatter = Formatter(
            "%(asctime)s: %(levelname)s [%(threadName)s] [%(module)s] %(funcName)s(%(lineno)d): %(message)s",
            "%Y-%m-%d %H:%M:%S",
        )

        self.console_handler = StreamHandler()
        self.console_handler.setFormatter(linear_formatter)

    def get_logger(self, name: str) -> Logger:
        logger = Logger(name)
        logger.setLevel(INFO)
        if self.console_handler not in logger.handlers:
            logger.addHandler(self.console_handler)

        return logger
