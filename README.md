# RabbitMQ Broker
[![Python versions](https://img.shields.io/badge/python-%3E=3.9-blue)](https://www.python.org/)
[![Docker version](https://img.shields.io/badge/Docker-23.0.1-blue)](https://www.docker.com//)
[![](https://img.shields.io/badge/-FastAPI-green)](https://fastapi.tiangolo.com/)
[![Black code style](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/ambv/black)
[![Isort imports](https://img.shields.io/badge/imports-isort-31674b1?style=flat&labelColor=ef8336)](https://pycqa.github.io/isort/)
![coverage](http://192.168.32.52/gazprom-asez/webportal-logic/badges/develop/coverage.svg) 

Не зависящий от фреймворков пакет для общения между микросервисами. Пакет предоставляет интерфейс для работы с брокером сообщений `RabbitMQ` и базовый класс цепочки обработчиков.

Пакет реализует паттерн цепочка обязанностей в синхронном и асинхронном виде.

## Конфигурация

| Переменная окружения  | Описание                              |     Значение по умолчанию     |
|-----------------------|---------------------------------------|-------------------------------|
| MICROSERVICE_SETTINGS | Путь к модулю настроек проекта отно-  |         "settings"            |
|                       | -сительно корня проекта. (Разделение  |                               |
|                       | через точку: module1.module2.settings)|                               |


## Использование

### Цепочка обработчиков

Для использования цепочки обязанностей нужно импортировать базовый класс звена и унаследоваться от него. Необходимо установить параметр `request_type`. Обязательно должен быть переопределен абстрактный метод `BaseChain.get_response_body(self, data)`:

```
from rmq_broker.chains.base import BaseChain


class LoginChain(BaseChain):
    request_type = "login"

    def get_response_body(self, data: dict) -> dict:
        ...
```

Также, можно унаследоваться от асинхронного варианта реализации:
```
from rmq_broker.async_chains.base import BaseChain
    
    
class LoginChain(BaseChain):
    request_type = "login"
    
    async def get_response_body(self, data: dict) -> dict:
        ...
```

Метод должен содержать логику обработки запроса и вызывать родительский метод 
`BaseChain.form_response(data, body, code, message)`
```
class LoginChain(BaseChain):
    request_type = "login"

    async def get_response_body(self, data):
        # Обработка запроса
        ...
        return super().form_response(data, response, status.HTTP_200_OK, "OK")
```

`data`: Изначальное сообщение.
`body`: Обработанное тело запроса.
`code`: HTTP код ответа.
`message`: Сообщение к ответу.

### RPC брокер

Запуск прослушки и автоматического ответа на сообщения.
В файле `consumer.py`:
```
from app.chains import your_chain
from rmq_broker.queues.rabbitmq import AsyncRabbitMessageQueue

async def broker_runner():
    async with AsyncRabbitMessageQueue() as provider:
        await provider.register_tasks("rpc_queue_name", your_chain.handle)
        await provider.consume()


asyncio.run(broker_runner())
```

Далее:
```
python3 consumer.py
```
