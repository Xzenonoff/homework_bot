import logging
import os
import time

import requests
import telegram
from dotenv import load_dotenv
from telegram import Bot

from exceptions import (EmptyListError, EndpointNot200Error,
                        RequestExceptionError, UndocumentedStatusError)

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s, %(levelname)s, %(message)s, %(name)s,',
    filename='kittybot.log',
    filemode='w',
    encoding='UTF-8'
)
logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Отправляет сообщение в Telegram."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info(f'Сообщение {message} - отправлено')
    except telegram.TelegramError as error:
        logger.error(f'Не удалось отправить сообщение: {error}')


def get_api_answer(current_timestamp):
    """Делает запрос к эндпоинту API-сервиса."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
        if response.status_code != 200:
            msg = f'{ENDPOINT} не доступен. Код ответа: {response.status_code}'
            logger.error(msg)
            raise EndpointNot200Error(msg)
        return response.json()
    except requests.exceptions.RequestException as request_error:
        msg = f'Код ответа API (RequestException): {request_error}'
        logger.error(msg)
        raise RequestExceptionError(msg)


def check_response(response):
    """Проверяет ответ API на корректность."""
    if not isinstance(response['homeworks'], list):
        msg = 'Неверный тип данных'
        logger.error(msg)
        raise TypeError(msg)
    if not response['homeworks']:
        msg = 'Пришел пустой список'
        logger.error(msg)
        raise EmptyListError(msg)
    homework_status = response['homeworks'][0].get('status')
    if homework_status not in HOMEWORK_STATUSES:
        logger.error(f'Недокументированный статус: {homework_status}')
    return response['homeworks']


def parse_status(homework):
    """Извлекает статус полученной домашней работы."""
    homework_name = homework['homework_name']
    homework_status = homework['status']
    if homework_status is None:
        parse_status_errors(
            'Пустое значение homework_status: ', homework_status)
    if homework_name is None:
        parse_status_errors(
            'Пустое значение homework_name: ', homework_name)
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def parse_status_errors(text, key):
    """Обрабатывает пустые значения."""
    msg = f'{text}{key}'
    logger.error(msg)
    raise UndocumentedStatusError(msg)


def check_tokens():
    """Проверяет доступность переменных окружения."""
    tokens = [
        (PRACTICUM_TOKEN, 'PRACTICUM_TOKEN'),
        (TELEGRAM_TOKEN, 'TELEGRAM_TOKEN'),
        (TELEGRAM_CHAT_ID, 'TELEGRAM_CHAT_ID')
    ]
    check_result = True
    for token, name in tokens:
        if token is None:
            logger.critical(
                f'Отсутствует обязательная переменная окружения: {name}'
            )
            check_result = False
    return check_result


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        exit()
    bot = Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    send_message(bot, 'Я начал работать')
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            if homeworks:
                message = parse_status(homeworks[0])
                send_message(bot, message)
            current_timestamp = int(time.time())
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
            logger.critical(message)
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
