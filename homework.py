import logging
import os
import sys
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

from exceptions import HTTPException, YandexAPIRequestError

load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    level=logging.DEBUG)
logger = logging.getLogger()
logger.addHandler(logging.StreamHandler(stream=sys.stdout))

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
THREE_MONTHS = 131400 * 60
LENGTH = 400
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверяет доступность переменных окружения.
    необходимых для работы программы.
    """
    if not PRACTICUM_TOKEN or not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        logger.critical(
            'отсутствие обязательных переменных'
            'окружения во время запуска бота'
        )
        sys.exit()
    return True


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message[:LENGTH]
        )
        logger.debug('удачная отправка сообщения в Telegram')
    except telegram.error.TelegramError:
        message = 'сбой при отправке сообщения в Telegram'
        logger.error(message, exc_info=True)
        raise Exception(message)


def get_api_answer(timestamp):
    """Делает запрос к API-сервису по временной метке."""
    try:
        response = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params={'from_date': timestamp}
        )
    except ConnectionError:
        raise ConnectionError('непроходит запрос к Yandex API.')
    except response.JSONDecodeError:
        raise TypeError('формат данных не JSON')
    if response.status_code != HTTPStatus.OK:
        code, text = response.status_code, response.text
        detail = f'Код ответа: {code}, сообщение об ошибке: {text}'
        if response.status_code != HTTPStatus.UNAUTHORIZED:
            raise HTTPException(f'ошибка авторизации от Yandex API. {detail}')
        if response.status_code != HTTPStatus.BAD_REQUEST:
            raise HTTPException(f'ошибка запроса к Yandex API. {detail}')
        raise response.RequestException(
            f'некорректный ответ от Yandex API. {detail}'
        )
    else:
        return response.json()


def check_response(response):
    """Проверяет ответ API на соответствие документации."""
    if type(response) is not dict:
        raise TypeError(
            'ответ API не соответствует документации (не словарь)'
        )
    if 'homeworks' not in response:
        logger.error('отсутствие ожидаемых ключей в ответе API')
        raise KeyError(
            'Отсутствуют необходимый ключ homeworks'
        )
    if type(response['homeworks']) is not list:
        raise TypeError(
            'ответ API не соответствует документации (не список)'
        )
    if type(response['homeworks'][0]) is not dict:
        raise TypeError(
            'ответ API не соответствует документации (не словарь)'
        )
    if type(response) is not dict:
        raise TypeError(
            'ответ API не соответствует документации (не словарь)'
        )
    try:
        response['homeworks'][0]
    except response.InvalidResponse as error:
        raise Exception(
            'неверный ответ'
        ) from error
    except Exception as error:
        raise Exception(
            'ошибка получения ответа по ключу'
        ) from error
    return response['homeworks'][0]


def parse_status(homework):
    """Извлекает из информации о конкретной.
    домашней работе статус этой работы.
    """
    try:
        homework_name = homework['homework_name']
        status = homework['status']
    except KeyError as error:
        raise YandexAPIRequestError(
            'отсутствие ожидаемых ключей в ответе API'
        ) from error
    try:
        verdict = HOMEWORK_VERDICTS[status]
    except KeyError as error:
        raise YandexAPIRequestError(
            'неожиданный статус домашней работы, обнаруженный в ответе API'
        ) from error
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time()) - THREE_MONTHS
    status, new_error = '', ''
    while True:
        try:
            logger.info('Начали вызов функций в main')
            check_tokens()
            response = get_api_answer(timestamp)
            homework = check_response(response)
            reply = parse_status(homework)
            if status != homework['status']:
                send_message(bot, reply)
            status = homework['status']
            logger.info('Закончили вызов функций в main')
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.exception(message)
            if not sys.exc_info() and error != new_error:
                send_message(bot, message)
                new_error = error
        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
