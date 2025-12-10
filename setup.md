# Развертывание сервиса

## Описание работы с каталогами

## Деплой сервиса

### Деплой сервиса в yc

**Шаг 1. Проверяем работоспособность сервиса.**

Запускаем сервис через sh скрипт:

```bash
./scripts/entrypoint_api.sh 
```

Запускаем автотесты:

```bash
make test
```

**Шаг 2. Собираем образ и деплоим его в Container Registry yc.**

Потребуется идентификатор реестра контейнеров в yc (container_registry_id) и нужно придумать название образа.

```bash
docker build -t cr.yandex/{container_registry_id}/{image_name}:latest .
docker push cr.yandex/{container_registry_id}/{image_name}:latest
```

**Шаг 3. Создание serverless container в yc.**

Если потребуется отдельный сервисный аккаунт, то нужно создать его до этого шага. При создании контейнера:

1. Выбираем новый образ
1. Выделяем ресурсы для контейнера. RAM не менее 256.
1. Выбираем образ из списка
1. Добавляем переменные окружения
1. Добавляем сервисный аккаунт
1. Жмем кнопку создать ревизию.
1. Запоминаем id созданного контейнера.

**Шаг 4. Настройка апи шлюза.**

Чтобы сервис был доступен по привязанному урлу, нужно перейти в раздел Serverless Integrations, API-шлюзы и выбрать нужный.

Далее допустим нужно чтобы все запросы к домену https://site.com и location начинающемуся с /api/v1/ (т.е. https://site.com/api/v1/) были перенаправлены в контейнер. Для этого проверяем, что:

1. В разделе servers yaml конфига указан домен:
```yaml
servers:
- url: https://d5dk123v2k7r08mekb6v7b.l3hh3szr.apigw.yandexcloud.net
- url: https://site.com
```
1. В раздел paths добавляем блок следующего содержания:
```yaml
  /api/v1/{proxy+}:
    x-yc-apigateway-any-method:
      x-yc-apigateway-integration:
        type: serverless_containers
        container_id: {container_id}
        service_account_id: {service_account_id}
      parameters:
      - explode: false
        in: path
        name: proxy
        required: false
        schema:
          default: '-'
          type: string
        style: simple
```
Потребуются id сервисного аккаунта и id контейнера из предыдущего шага.

**ВАЖНО: Т.к. api шлюз не убирает из location путь /api/v1/, то нужно чтобы роуты внутри приложения тоже этот путь учитывали.**

**Шаг 5. Проверяем доступность сервиса.**
