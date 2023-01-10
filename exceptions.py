class CheckOutProjectException(Exception):
    """Основные исключения для проекта."""


class HTTPException(CheckOutProjectException):
    """Исключения при получения ответа от HTTP."""


class YandexAPIRequestError(CheckOutProjectException):
    """Исключения при обращении к API Yandex."""

class MessageError(CheckOutProjectException):
    """Cбой при отправке сообщения в Telegram."""

