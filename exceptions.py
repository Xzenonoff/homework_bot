class EndpointNot200Error(Exception):
    """Ответ сервера не равен 200."""


class RequestExceptionError(Exception):
    """Ошибка обработки запроса."""


class UndocumentedStatusError(Exception):
    """Недокументированный статус."""
