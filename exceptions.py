class EndpointNot200Error(Exception):
    """Ответ сервера не равен 200."""


class RequestExceptionError(Exception):
    """Ошибка обработки запроса."""


class EmptyListError(Exception):
    """Пришел пустой список."""


class UndocumentedStatusError(Exception):
    """Недокументированный статус."""
