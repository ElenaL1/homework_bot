# homework_bot
Telegram-бот, который обращается к API сервису и проверяет статус отправленной на ревью.

### Что делает бот:
-   раз в 10 минут опрашивать API сервиса и проверять статус отправленной на ревью работы;
-   при обновлении статуса анализирует ответ API и отправляет соответствующее уведомление в Telegram;
-   логирует свою работу и сообщает о проблемах с сообщением в Telegram.

### Стек технологий:
Python, Django
