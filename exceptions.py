class ServerStatusError(Exception):
    """Ответ сервера не равен 200."""
    pass


class UndocumentedStatusError(Exception):
    """Недокументированный статус."""
    pass


class EmptyListError(Exception):
    """Получен пустой список."""
    pass


class TokenError(Exception):
    """Получен пустой список."""
    pass
