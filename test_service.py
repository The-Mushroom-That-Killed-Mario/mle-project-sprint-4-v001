
"""Тестирование FastAPI-сервиса музыкальных рекомендаций."""

import logging

import requests


# Настраиваем подключение и логирование

BASE_URL = "http://127.0.0.1:8000"
TIMEOUT = 180

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(
            "test_service.log",
            mode="w",
            encoding="utf-8"
        ),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def get_recommendations(user_id: int, k: int = 10) -> dict:
    """Отправляем запрос на получение рекомендаций."""

    response = requests.get(
        f"{BASE_URL}/recommendations",
        params={
            "user_id": user_id,
            "k": k
        },
        timeout=TIMEOUT
    )

    response.raise_for_status()
    return response.json()


def add_interaction(user_id: int, track_id: int) -> dict:
    """Регистрируем новое прослушивание."""

    response = requests.post(
        f"{BASE_URL}/events",
        json={
            "user_id": user_id,
            "track_id": track_id
        },
        timeout=TIMEOUT
    )

    response.raise_for_status()
    return response.json()


def clear_history(user_id: int):
    """Очищаем историю перед тестированием."""

    response = requests.delete(
        f"{BASE_URL}/events/{user_id}",
        timeout=TIMEOUT
    )

    response.raise_for_status()


def check_recommendations(result: dict, user_id: int):
    """Проверяем структуру и корректность ответа."""

    assert result["user_id"] == user_id
    assert isinstance(result["recommendations"], list)
    assert len(result["recommendations"]) == 10
    assert len(set(result["recommendations"])) == 10
    assert all(
        isinstance(track_id, int)
        for track_id in result["recommendations"]
    )


def test_without_personal_recommendations():
    """Проверяем пользователя без персональных рекомендаций."""

    user_id = 999999999

    clear_history(user_id)

    result = get_recommendations(user_id)

    check_recommendations(result, user_id)

    assert result["source"] == "popular"

    logger.info("Тест 1: пользователь без персональных рекомендаций")
    logger.info("Результат: %s", result)
    logger.info("Статус: PASSED")


def test_without_online_history():
    """Проверяем пользователя с персональными рекомендациями без онлайн-истории."""

    user_id = 0

    clear_history(user_id)

    result = get_recommendations(user_id)

    check_recommendations(result, user_id)

    assert result["source"] == "offline"

    logger.info("Тест 2: пользователь без онлайн-истории")
    logger.info("Результат: %s", result)
    logger.info("Статус: PASSED")


def test_with_online_history():
    """Проверяем смешивание рекомендаций после нового прослушивания."""

    user_id = 0
    track_id = 26

    clear_history(user_id)

    add_interaction(
        user_id=user_id,
        track_id=track_id
    )

    result = get_recommendations(user_id)

    check_recommendations(result, user_id)

    assert result["source"] == "mixed"
    assert track_id not in result["recommendations"]

    logger.info("Тест 3: пользователь с онлайн-историей")
    logger.info("Результат: %s", result)
    logger.info("Статус: PASSED")


def main():
    """Последовательно выполняем три тестовых сценария."""

    logger.info("Начало тестирования сервиса")

    tests = [
        test_without_personal_recommendations,
        test_without_online_history,
        test_with_online_history
    ]

    passed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception:
            logger.exception(
                "Тест %s: FAILED",
                test.__name__
            )

    logger.info(
        "Итог: %s/%s тестов пройдено",
        passed,
        len(tests)
    )

    if passed != len(tests):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
