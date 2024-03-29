import logging
import os
import time
from logging.handlers import RotatingFileHandler

import requests
from dotenv import load_dotenv
from requests.exceptions import RequestException
from telegram import Bot, TelegramError

from exceptions import ServerStatusError, TokenError, UndocumentedStatusError

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

TOKENS = ('PRACTICUM_TOKEN', 'TELEGRAM_TOKEN', 'TELEGRAM_CHAT_ID')

PARSE_MSG = '{text}{key}'
GET_API_ERROR = (
    '{ENDPOINT} не доступен. Заголовки: {HEADERS}. '
    'Параметры: {params}. {description}'
)


def send_message(bot, message):
    """Отправляет сообщение в Telegram."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.info(f'Сообщение: {message} - отправлено')
    except TelegramError as error:
        raise TelegramError(
            f'Не удалось отправить сообщение пользователю: {TELEGRAM_CHAT_ID}.'
            f' Ошибка: {error}'
        )


def get_api_answer(current_timestamp):
    """Делает запрос к эндпоинту API-сервиса."""
    logging.info('Запрос к эндпоинту')
    params = {'from_date': current_timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    except RequestException as request_err:
        raise ConnectionError(
            GET_API_ERROR.format(
                ENDPOINT=ENDPOINT,
                HEADERS=HEADERS,
                params=params,
                description=f'Код ответа API (RequestException): {request_err}'
            )
        )
    if response.status_code != 200:
        raise ServerStatusError(
            GET_API_ERROR.format(
                ENDPOINT=ENDPOINT,
                HEADERS=HEADERS,
                params=params,
                description=f'Код ответа: {response.status_code}'
            )
        )
    return response.json()


def check_response(response):
    """Проверяет ответ API на корректность."""
    if not isinstance(response, dict):
        raise TypeError(
            f'response не является словарем. Текущий тип: {type(response)}'
        )
    homeworks = response['homeworks']
    if not isinstance(homeworks, list):
        raise TypeError(
            f'homeworks_list не является списком. '
            f'Текущий тип: {type(homeworks)}'
        )
    return homeworks


def parse_status(homework):
    """Извлекает статус полученной домашней работы."""
    homework_name = homework['homework_name']
    homework_status = homework['status']
    if homework_status is None:
        raise KeyError(f'Пустое значение homework_status: {homework_status}')
    if homework_name is None:
        parse_status_errors(
            'Пустое значение homework_name: ', homework_name
        )
    if homework_status not in HOMEWORK_VERDICTS:
        parse_status_errors(
            'Недокументированный статус: ', homework_status
        )
    verdict = HOMEWORK_VERDICTS[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def parse_status_errors(text, key):
    """Обрабатывает пустые значения."""
    raise UndocumentedStatusError(PARSE_MSG.format(text=text, key=key))


def check_tokens():
    """Проверяет доступность переменных окружения."""
    check_result = True
    for token in TOKENS:
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
    last_error = ''
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            if homeworks:
                message = parse_status(homeworks[0])
            else:
                message = 'Нет новых работ'
            if last_msg != message:
                send_message(bot, message)
                last_msg = message
            else:
                logging.info('Статус работ не изменился')
            current_timestamp = response.get('current_date', int(time.time()))
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.critical(message)
            if last_error != message:
                send_message(bot, message)
                last_error = message
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
            RotatingFileHandler(
                __file__ + '.log',
                encoding='UTF-8',
                backupCount=5,
                maxBytes=20000
            )
        ]
    )
    main()
