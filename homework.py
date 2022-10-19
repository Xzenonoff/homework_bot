import logging
import os
import time

import requests
import telegram
from dotenv import load_dotenv
from requests.exceptions import RequestException
from telegram import Bot

from exceptions import (
    EmptyListError, ServerStatusError, TokenError, UndocumentedStatusError
)

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

PARSE_MSG = '{text}{key}'


def send_message(bot, message):
    """Отправляет сообщение в Telegram."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.info(f'Сообщение {message} - отправлено')
    except telegram.TelegramError:
        raise telegram.TelegramError(
            f'Не удалось отправить сообщение пользователю: {TELEGRAM_CHAT_ID}'
        )


def get_api_answer(current_timestamp):
    """Делает запрос к эндпоинту API-сервиса."""
    logging.info('Запрос к эндпоинту')
    params = {'from_date': current_timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    except RequestException as request_error:
        raise ConnectionError(
            f'Код ответа API (RequestException): {request_error}'
        )
    if response.status_code != 200:
        msg = (
            f'{ENDPOINT} не доступен. '
            f'Заголовки: {HEADERS}. '
            f'Параметры: {params}. '
            f'Код ответа: {response.status_code}'
        )
        raise ServerStatusError(msg)
    return response.json()


def check_response(response):
    """Проверяет ответ API на корректность."""
    if not isinstance(response, dict):
        raise TypeError('response не является словарем')
    if not isinstance(response['homeworks'], list):
        raise TypeError("response['homeworks'] не является списком")
    if not response['homeworks']:
        raise EmptyListError('Пришел пустой список')
    return response['homeworks']


def parse_status(homework):
    """Извлекает статус полученной домашней работы."""
    homework_name = homework['homework_name']
    homework_status = homework['status']
    if homework_status is None:
        parse_status_errors(
            'Пустое значение homework_status: ', homework_status
        )
    if homework_name is None:
        parse_status_errors(
            'Пустое значение homework_name: ', homework_name
        )
    if homework_status not in VERDICTS:
        parse_status_errors(
            'Недокументированный статус: ', homework_status
        )
    verdict = VERDICTS[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def parse_status_errors(text, key):
    """Обрабатывает пустые значения."""
    raise UndocumentedStatusError(PARSE_MSG.format(text=text, key=key))


def check_tokens():
    """Проверяет доступность переменных окружения."""
    tokens = ('PRACTICUM_TOKEN', 'TELEGRAM_TOKEN', 'TELEGRAM_CHAT_ID')
    check_result = True
    for token in tokens:
        value = globals()[token]
        if value is None:
            logging.critical(
                f'Отсутствует обязательная переменная окружения: {token}'
            )
            check_result = False
    return check_result


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        raise TokenError('Token(ы) не найден(ы)')
    bot = Bot(token=TELEGRAM_TOKEN)
    current_timestamp = 0
    send_message(bot, 'Я начал работать')
    last_msg = ''
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            message = parse_status(homeworks[0])
            if homeworks and last_msg != message:
                send_message(bot, message)
                last_msg = message
            current_timestamp = int(time.time())
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
            logging.critical(message)
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format=(
            '%(levelname)s,'
            '%(lineno)s,'
            '%(funcName)s,'
            '%(asctime)s,'
            '%(message)s,'
            '%(name)s,'
        ),
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(__file__ + '.log', encoding='UTF-8')
        ]
    )
    main()
