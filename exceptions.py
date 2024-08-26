class NotForSending(Exception):
    """Не для пересылки в телеграм."""


class ProblemDescriptions(Exception):
    """Описания проблемы."""


class InvalidResponseCode(Exception):
    """Не верный код ответа."""


class HomeworkStatusIsNotDocumented(Exception):
    """Статус не задокументирован."""


class AbsentAPI(Exception):
    """Не хватает глобаной переменной."""


class RequestError(Exception):
    """Недоступность сервера."""


class ConnectinError(Exception):
    """Не верный код ответа."""


class EmptyResponseFromAPI(NotForSending):
    """Пустой ответ от API."""


class TelegramError(NotForSending):
    """Ошибка телеграма."""
