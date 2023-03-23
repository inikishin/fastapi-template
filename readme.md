# Шаблон микросервиса на FastAPI

Данный шаблон предназначен для быстрого развертывания микросервиса на [FastAPI](https://fastapi.tiangolo.com/) и включает в себя следующие компоненты:

- данный readme.md файл;
- структуру каталогов микросервиса;
- requirements.txt для установки зависимостей;
- Makefile с различными командами, описание которых дано ниже.

## Makefile описание команд

```shell
make install
```

Установка необходимых зависимостей.

```shell
make run
```

Запуск сервера локально.

```shell
make lint
```

Запуск линтеров.

```shell
make test
```

Запуск тестов.

```shell
make migrate msg=migration-description
```

Создать автомиграцию с описанием из параметра msg

```shell
make upgrade
```

Применить все миграции

```shell
make downgrade
```

Откатить последнюю миграцию

```shell
make history
```

Показать историю миграций алембика
