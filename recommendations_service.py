
"""FastAPI-сервис для выдачи музыкальных рекомендаций."""

from collections import defaultdict
from pathlib import Path
from threading import Lock

import pandas as pd
import pyarrow.dataset as ds
from fastapi import FastAPI, Query
from pydantic import BaseModel, Field


# ============================================================
# Конфигурация
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

RECOMMENDATIONS_PATH = (
    BASE_DIR / "recommendations" / "recommendations.parquet"
)

SIMILAR_PATH = (
    BASE_DIR / "recommendations" / "similar" / "similar.parquet"
)

TOP_POPULAR_PATH = (
    BASE_DIR / "recommendations" / "top_popular" / "top_popular.parquet"
)

HISTORY_SIZE = 5
ONLINE_SHARE = 0.5


# ============================================================
# Схемы запросов и ответов
# ============================================================

class InteractionRequest(BaseModel):
    """Новое прослушивание пользователя."""

    user_id: int = Field(ge=0)
    track_id: int = Field(ge=0)


class RecommendationResponse(BaseModel):
    """Ответ сервиса рекомендаций."""

    user_id: int
    recommendations: list[int]
    source: str


# ============================================================
# Обработчик рекомендаций
# ============================================================

class RecommendationHandler:
    """Обрабатываем запросы и формируем рекомендации."""

    def __init__(self):
        """Подключаем источники и инициализируем онлайн-историю."""

        self.recommendations = ds.dataset(
            RECOMMENDATIONS_PATH,
            format="parquet"
        )

        self.similar = ds.dataset(
            SIMILAR_PATH,
            format="parquet"
        )

        self.top_popular = pd.read_parquet(
            TOP_POPULAR_PATH
        ).sort_values("rank")

        self.online_history = defaultdict(list)
        self.history_lock = Lock()

    def add_interaction(
        self,
        user_id: int,
        track_id: int
    ) -> dict:
        """Добавляем прослушанный трек в онлайн-историю."""

        with self.history_lock:
            self.online_history[user_id].append(track_id)

        return {
            "user_id": user_id,
            "track_id": track_id,
            "status": "ok"
        }

    def get_user_history(
        self,
        user_id: int
    ) -> list[int]:
        """Получаем сохранённую онлайн-историю пользователя."""

        with self.history_lock:
            return list(
                self.online_history.get(user_id, [])
            )

    def clear_history(
        self,
        user_id: int
    ) -> dict:
        """Очищаем онлайн-историю пользователя для тестирования."""

        with self.history_lock:
            self.online_history.pop(user_id, None)

        return {
            "user_id": user_id,
            "status": "cleared"
        }

    def get_offline_recommendations(
        self,
        user_id: int,
        k: int = 10
    ) -> list[int]:
        """Получаем заранее рассчитанные персональные рекомендации."""

        recommendations = (
            self.recommendations
            .to_table(
                columns=["track_id", "rank"],
                filter=ds.field("user_id") == user_id
            )
            .to_pandas()
        )

        if recommendations.empty:
            return []

        return (
            recommendations
            .sort_values("rank")
            .head(k)["track_id"]
            .astype(int)
            .tolist()
        )

    def get_popular_recommendations(
        self,
        k: int = 10
    ) -> list[int]:
        """Получаем наиболее популярные треки."""

        return (
            self.top_popular
            .head(k)["track_id"]
            .astype(int)
            .tolist()
        )

    def get_online_recommendations(
        self,
        user_id: int,
        k: int = 10
    ) -> list[int]:
        """Подбираем похожие треки по последним прослушиваниям."""

        history = self.get_user_history(user_id)

        if not history:
            return []

        recent_tracks = list(
            dict.fromkeys(reversed(history))
        )[:HISTORY_SIZE]

        similar_tracks = (
            self.similar
            .to_table(
                columns=[
                    "track_id",
                    "similar_track_id",
                    "score",
                ],
                filter=ds.field("track_id").isin(recent_tracks)
            )
            .to_pandas()
        )

        if similar_tracks.empty:
            return []

        # Более свежим прослушиваниям отдаём приоритет

        priority = {
            track_id: index
            for index, track_id in enumerate(recent_tracks)
        }

        similar_tracks["priority"] = (
            similar_tracks["track_id"]
            .map(priority)
        )

        similar_tracks = (
            similar_tracks
            .sort_values(
                ["priority", "score"],
                ascending=[True, False]
            )
        )

        # Исключаем прослушанные треки и повторения

        similar_tracks = similar_tracks[
            ~similar_tracks["similar_track_id"].isin(history)
        ]

        similar_tracks = similar_tracks.drop_duplicates(
            subset="similar_track_id"
        )

        return (
            similar_tracks
            .head(k)["similar_track_id"]
            .astype(int)
            .tolist()
        )

    def mix_recommendations(
        self,
        offline: list[int],
        online: list[int],
        history: list[int],
        k: int = 10
    ) -> list[int]:
        """Смешиваем рекомендации и исключаем повторы."""

        if not online:
            candidates = offline
        else:
            online_count = int(k * ONLINE_SHARE)

            candidates = (
                online[:online_count]
                + offline[:k - online_count]
                + online[online_count:]
                + offline[k - online_count:]
            )

        # Исключаем треки из истории и дубликаты

        seen = set(history)
        result = []

        for track_id in candidates:
            if track_id in seen:
                continue

            seen.add(track_id)
            result.append(track_id)

            if len(result) >= k:
                break

        # Добираем популярными треками, если рекомендаций мало

        if len(result) < k:
            for track_id in self.get_popular_recommendations(k=100):
                if track_id in seen:
                    continue

                seen.add(track_id)
                result.append(track_id)

                if len(result) >= k:
                    break

        return result

    def handle(
        self,
        user_id: int,
        k: int = 10
    ) -> dict:
        """Формируем итоговые рекомендации пользователя."""

        history = self.get_user_history(user_id)

        offline = self.get_offline_recommendations(
            user_id=user_id,
            k=100
        )

        has_personal = bool(offline)

        if not has_personal:
            offline = self.get_popular_recommendations(
                k=100
            )

        online = self.get_online_recommendations(
            user_id=user_id,
            k=100
        )

        recommendations = self.mix_recommendations(
            offline=offline,
            online=online,
            history=history,
            k=k
        )

        if online:
            source = "mixed"
        elif has_personal:
            source = "offline"
        else:
            source = "popular"

        return {
            "user_id": user_id,
            "recommendations": recommendations,
            "source": source
        }


# ============================================================
# FastAPI-приложение
# ============================================================

app = FastAPI(
    title="Music Recommendation Service",
    version="1.0.0"
)

handler = RecommendationHandler()


@app.get("/")
def read_root():
    """Проверяем доступность сервиса."""

    return {
        "service": "music_recommendation",
        "status": "ok"
    }


@app.post("/events")
def add_event(request: InteractionRequest):
    """Регистрируем новое прослушивание пользователя."""

    return handler.add_interaction(
        user_id=request.user_id,
        track_id=request.track_id
    )


@app.delete("/events/{user_id}")
def clear_events(user_id: int):
    """Очищаем онлайн-историю пользователя для тестирования."""

    return handler.clear_history(
        user_id=user_id
    )


@app.get(
    "/recommendations",
    response_model=RecommendationResponse
)
def get_recommendations(
    user_id: int = Query(ge=0),
    k: int = Query(default=10, ge=1, le=100)
):
    """Получаем итоговые музыкальные рекомендации."""

    return handler.handle(
        user_id=user_id,
        k=k
    )
