class ParserFindTagException(Exception):
    """Вызывается, когда парсер не может найти тег."""
    pass


class VersionsNotFoundException(Exception):
    """Вызывается, когда парсер не может найти список `All versions`."""
    pass
