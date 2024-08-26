import logging
import os
import time
import sys
from http import HTTPStatus

import requests
import telebot
from dotenv import load_dotenv

import exceptions


load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TOKEN')
TELEGRAM_CHAT_ID = os.getenv('CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверка доступности переменных окружения."""
    required_tokens = {
        'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
        'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
        'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID
    }
    missing_tokens = []
    for token_name, token_value in required_tokens.items():
        if not token_value:
            missing_tokens.append(token_name)
    if missing_tokens:
        missing_tokens_str = "\n- ".join(missing_tokens)
        logging.critical(
            f"Переменные окружения отсутствуют:\n- {missing_tokens_str}"
        )
        raise exceptions.AbsentAPI('Не хватает глобаной переменной')


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    try:
        logging.info('Начало отправки')
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message,
        )
    except (telebot.apihelper.ApiException,
            requests.exceptions.RequestException) as error:
        logging.error(f'Ошибка при отправке сообщения: {error}')
        return False
    else:
        logging.debug(f'Сообщение успешно отправлено: {message}')
        return True


def get_api_answer(current_timestamp):
    """Получить статус домашней работы."""
    params_request = {
        'url': ENDPOINT,
        'headers': HEADERS,
        'params': {'from_date': current_timestamp},
    }
    try:
        logging.info(
            'Начало запроса: url = {url},'
            'headers = {headers},'
            'params = {params}'.format(**params_request))
        homework_statuses = requests.get(**params_request)
    except requests.RequestException as error:
        logging.error(error)
    if homework_statuses.status_code != HTTPStatus.OK:
        raise exceptions.InvalidResponseCode(
            'Не удалось получить ответ API, '
            f'ошибка: {homework_statuses.status_code}'
            f'причина: {homework_statuses.reason}'
            f'текст: {homework_statuses.text}')
    return homework_statuses.json()


def check_response(response):
    """Проверить валидность ответа."""
    logging.debug('Начало проверки')
    if not isinstance(response, dict):
        raise TypeError('Ошибка ответа API: response должен'
                        f'быть словарем, получен тип {type(response)}')
    if 'homeworks' not in response or 'current_date' not in response:
        raise TypeError('Ошибка ответа API: ключи "homeworks" и '
                        '"current_date" отсутствуют в ответе')
    homeworks = response.get('homeworks')
    if not isinstance(homeworks, list):
        raise TypeError('Ошибка ответа API: "homeworks" должен быть'
                        f'списком, получен тип {type(homeworks)}')
    return homeworks


def parse_status(homework):
    """Распарсить ответ."""
    if 'status' not in homework:
        raise KeyError("Key 'status' is missing in the homework dictionary")
    status = homework['status']
    if 'homework_name' not in homework:
        raise KeyError('homework_name is not in dict')
    if not status:
        raise exceptions.HomeworkStatusIsNotDocumented(
            'The homework does not have a status'
        )
    if status not in HOMEWORK_VERDICTS:
        raise exceptions.HomeworkStatusIsNotDocumented(
            'The status of homework is not documented'
        )
    homework_name = homework['homework_name']
    verdict = HOMEWORK_VERDICTS[status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    check_tokens()
    bot = telebot.TeleBot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    status = ''
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            if not homeworks:
                logging.debug('No status changes')
            else:
                last_homework = homeworks[0]
                message = parse_status(last_homework)
                if send_message(bot, message):
                    current_timestamp = response.get('current_date')
                status = message
        except Exception as error:
            message = f'Error while running the program: {error}'
            logging.error(message)
            if status != message:
                send_message(bot, message)
                status = message
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format=(
            '%(asctime)s, %(levelname)s, Путь - %(pathname)s, '
            'Файл - %(filename)s, Функция - %(funcName)s, '
            'Номер строки - %(lineno)d, %(message)s'
        ),
        handlers=[logging.FileHandler('log.txt', encoding='UTF-8'),
                  logging.StreamHandler(sys.stdout)])
    main()
