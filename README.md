# Хранилище мероприятий

Данный документ содержит описание работы и информацию о развертке микросервиса-обертки для хранилища информации о мероприятиях

Название сервиса: `event_das`

Структура сервиса:

| Файл                       | Описание                                                          |
| -------------------------- | ----------------------------------------------------------------- |
| `event_das.py`             | Код микросервиса                                                  |
| `config.yml`               | Конфигурационный файл со строкой подключения к RabbitMQ и MongoDB |
| `run.sh`                   | Файл для запуска сервиса из Docker контейнера                     |
| `requirements.txt`         | Верхнеуровневые зависимости                                       |
| `requirements.lock`        | Все зависимости (`pip freeze`)                                    |
| `Dockerfile`               | Описание сборки контейнера сервиса                                |
| `docker-compose.yml`       | Изолированная развертка сервиса вместе с (RabbitMQ, MongoDB)      |
| `docker-compose.local.yml` | Развертка зависимостей для дебаггинга (RabbitMQ, MongoDB)         |
| `.rest`                    | Тесты взаимодействия с HTTP эндпоинтами микросервиса              |
| `README.md`                | Описание микросервиса                                             |

## API

### RPC

Сохранить мероприятия:

```bat
n.rpc.event_das.save_events(events)

Args: list of events
Returns: nothing
```

Получить мероприятие по его ид:

```bat
n.rpc.event_das.get_event_by_id(event_id)

Args: event_id
Return: event as dictionary object
```

Получить мероприятия, отсортированные по дате:

```bat
n.rpc.event_das.get_events_by_date()

Args: nothing
Returns: list of actual events sorted by date
```

Получить тэги мероприятия по его ид:

```bat
n.rpc.event_das.get_tags_by_id(event_id)

Args: event_id
Returns: list of all tags related to the event
```

Получить список ид всех мероприятий с их тэгами в виде словаря:

```bat
n.rpc.event_das.get_event_tags()

Args: nothing
Returns: events like {'event_1_id': ['tag_1',...,'tag_n'], ..., 'event_m_id':['tag_1',...,'tag_k']}
```

### HTTP

Сохранить мероприятия:

```rst
POST http://localhost:8000/events HTTP/1.1
Content-Type: application/json

[
  {
    "title": "Видео+Конференция 2020",
    "type": "Конференция",
    "isPaid": true,
    "isOnline": true,
    "location": "Москва, Россия",
    "startDate": "13.10.2020",
    "endDate": "14.10.2020",
    "description": "...",
    "meta": {
      "it_events_crawler": "18960"
    }
  }, ..., {}
]
```

Получить мероприятия, отсортированные по дате:

```rst
GET http://localhost:8000/allevents HTTP/1.1
```

Получить тэги мероприятия по его ид:

```rst
GET http://localhost:8000/events/<string:id>/tags HTTP/1.1
```

Получить список ид всех мероприятий с их тэгами в виде словаря:

```rst
GET http://localhost:8000/tags HTTP/1.1
```

## Развертывание и запуск

### Локальный запуск

Для локального запуска микросервиса требуется запустить контейнер с RabbitMQ и MongoDB. Для этого есть специальный `docker-compose.local.yml`. Чтобы запустить:

```bat
docker-compose --file docker-compose.local.yml up -d
```

Затем из папки микросервиса вызвать

```bat
nameko run event_das
```

Для проверки `rpc` запустите в командной строке:

```bat
nameko shell
```

После чего откроется интерактивная Python среда. Обратитесь к сервису одной из команд, представленных выше в разделе `rpc`

### Запуск в контейнере

Чтобы запустить микросервис в контейнере вызовите команду:

```bat
docker-compose up
```

> если вы не хотите просмотривать логи, добавьте флаг `-d` в конце

Микросервис запустится вместе с RabbitMQ и MongoDB в контейнерах.

> Во всех случаях запуска вместе с MongoDB также разворачивается mongo-express - инструмент, с помощью которого можно просматривать и изменять содержимое подключенной базы (подключение в контейнерах сконфигурировано и производится автоматически). Сервис хостится локально на порту 8081.
