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
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
MESSAGE_ERROR = False
HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверяет доступность переменных окружения.
    необходимых для работы программы.
    """
    if not all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]):
        logger.critical(
            'отсутствие обязательных переменных'
            'окружения во время запуска бота'
        )
        sys.exit()
    return


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message
        )
        logger.debug('удачная отправка сообщения в Telegram')
    except telegram.error.TelegramError:
        global MESSAGE_ERROR
        MESSAGE_ERROR = True
        logger.error('сбой при отправке сообщения в Telegram')


def get_api_answer(timestamp):
    """Делает запрос к API-сервису по временной метке."""
    try:
        response = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params={'from_date': timestamp}
        )
    except Exception:
        logger.error('недоступность эндпоинта')
        raise YandexAPIRequestError('непроходит запрос к Yandex API.')
    if response.status_code != HTTPStatus.OK:
        code, text = response.status_code, response.text
        detail = f'Код ответа: {code}, сообщение об ошибке: {text}'
        logger.error(detail)
        if response.status_code == HTTPStatus.UNAUTHORIZED:
            raise HTTPException(f'ошибка авторизации от Yandex API. {detail}')
        if response.status_code == HTTPStatus.BAD_REQUEST:
            raise HTTPException(f'ошибка запроса к Yandex API. {detail}')
        raise response.RequestException(
            f'некорректный ответ от Yandex API. {detail}'
        )
    try:
        answer = response.json()
    except answer.JSONDecodeError:
        raise TypeError('формат данных не JSON')
    return answer


def check_response(response):
    """Проверяет ответ API на соответствие документации."""
    if type(response) is not dict:
        logger.error('ответ API не соответствует документации (не словарь)')
        raise TypeError(
            'ответ API не соответствует документации (не словарь)'
        )
    if 'homeworks' not in response:
        logger.error('отсутствие ожидаемого ключа homeworks в ответе API')
        raise KeyError(
            'Отсутствуют необходимый ключ homeworks'
        )
    if type(response['homeworks']) is not list:
        logger.error('ответ API не соответствует документации (не список)')
        raise TypeError(
            'ответ API не соответствует документации (не список)'
        )
    return response


def parse_status(homework):
    """Извлекает из информации о конкретной.
    домашней работе статус этой работы.
    """
    homework_name = homework.get('homework_name')
    status = homework.get('status')
    if homework_name is None or status is None:
        raise KeyError(
            'отсутствие ожидаемых ключей homework_name'
            'и/или status в ответе API'
        )
    verdict = HOMEWORK_VERDICTS.get(status)
    if verdict is None:
        error_detail = ('неожиданный статус домашней работы,'
                        'обнаруженный в ответе API'
                        )
        logger.error(error_detail)
        raise KeyError(error_detail)
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    check_tokens()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time()) - THREE_MONTHS
    new_error = ''
    while True:
        try:
            logger.info('Начали вызов функций в main')
            response = get_api_answer(timestamp)
            check_response(response)
            if len(response.get('homeworks')) != 0:
                homework = response['homeworks'][0]
                reply = parse_status(homework)
                send_message(bot, reply)
            else:
                logger.debug('отсутствие в ответе новых статусов')
            timestamp = response.get('current_date', timestamp)
            new_error = ''
            logger.info('Закончили вызов функций в main')
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            if not MESSAGE_ERROR or error != new_error:
                send_message(bot, message)
                new_error = error
        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
