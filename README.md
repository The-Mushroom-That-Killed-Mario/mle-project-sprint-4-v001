# Подготовка виртуальной машины

## Склонируйте репозиторий

Склонируйте репозиторий проекта:

```
git clone https://github.com/yandex-praktikum/mle-project-sprint-4-v001.git
```

## Активируйте виртуальное окружение

Используйте то же самое виртуальное окружение, что и созданное для работы с уроками. Если его не существует, то его следует создать.

Создать новое виртуальное окружение можно командой:

```
python3 -m venv env_recsys_start
```

После его инициализации следующей командой

```
. env_recsys_start/bin/activate
```

установите в него необходимые Python-пакеты следующей командой

```
pip install -r requirements.txt
```

### Скачайте файлы с данными

Для начала работы понадобится три файла с данными:
- [tracks.parquet](https://storage.yandexcloud.net/mle-data/ym/tracks.parquet)
- [catalog_names.parquet](https://storage.yandexcloud.net/mle-data/ym/catalog_names.parquet)
- [interactions.parquet](https://storage.yandexcloud.net/mle-data/ym/interactions.parquet)
 
Скачайте их в директорию локального репозитория. Для удобства вы можете воспользоваться командой wget:

```
wget https://storage.yandexcloud.net/mle-data/ym/tracks.parquet

wget https://storage.yandexcloud.net/mle-data/ym/catalog_names.parquet

wget https://storage.yandexcloud.net/mle-data/ym/interactions.parquet
```

## Запустите Jupyter Lab

Запустите Jupyter Lab в командной строке

```
jupyter lab --ip=0.0.0.0 --no-browser
```

# Расчёт рекомендаций

Код для выполнения первой части проекта находится в файле `recommendations.ipynb`. Изначально, это шаблон. Используйте его для выполнения первой части проекта.

# Сервис рекомендаций

Код сервиса рекомендаций находится в файле `recommendations_service.py`.

Из корневой директории проекта выполните:

```shell
uvicorn recommendations_service:app --host 127.0.0.1 --port 8000
```
Сервис запускается с одним worker, поскольку онлайн-история хранится в памяти процесса.

После запуска доступны:

http://127.0.0.1:8000/ — проверка состояния сервиса.

http://127.0.0.1:8000/docs — Swagger UI с описанием API.

# Инструкции для тестирования сервиса

Код для тестирования сервиса находится в файле `test_service.py`.

В первом терминале запустите сервис:
```shell
uvicorn recommendations_service:app --host 127.0.0.1 --port 8000
```
Во втором терминале, из корня проекта, выполните:
```shell
python test_service.py
```
## Проверяемые сценарии

| № | Сценарий | Ожидаемый результат |
|---|---|---|
| 1 | Пользователь без персональных рекомендаций | Выдаются популярные треки (`popular`) |
| 2 | Пользователь с персональными рекомендациями, но без онлайн-истории | Выдаются офлайн-рекомендации (`offline`) |
| 3 | Пользователь с персональными рекомендациями и онлайн-историей | Выдаются смешанные рекомендации (`mixed`) |

# Результаты проекта

Основные файлы для проверки:

    recommendations.ipynb — расчёт рекомендаций и оценка их качества.

    recommendations_service.py — FastAPI-микросервис.

    test_service.py — автоматизированное тестирование.

    test_service.log — фактический вывод тестирования.

    README.md — инструкции по подготовке, запуску и тестированию проекта.