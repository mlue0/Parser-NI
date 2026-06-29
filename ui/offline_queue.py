"""Офлайн-очередь: хранит данные для отправки когда API недоступен."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from logs.setup import get_logger

logger = get_logger(__name__)


def _queue_path() -> Path:
    from config.settings import BASE_DIR
    return BASE_DIR / "config" / "offline_queue.json"


def _load_queue() -> list[dict[str, Any]]:
    p = _queue_path()
    if not p.exists():
        return []
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def _save_queue(queue: list[dict[str, Any]]) -> None:
    p = _queue_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(queue, ensure_ascii=False, indent=2), encoding="utf-8")


def enqueue(data: dict[str, Any], file_path: str) -> None:
    """Добавляет данные в офлайн-очередь."""
    queue = _load_queue()
    queue.append({
        "queued_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "file_path": file_path,
        "data": data,
    })
    _save_queue(queue)
    logger.info("Добавлено в офлайн-очередь: %s (всего %d)", file_path, len(queue))


def queue_size() -> int:
    return len(_load_queue())


def flush_queue(api_client) -> tuple[int, int]:
    """Пытается отправить все записи из очереди.

    Returns:
        (sent, failed) — количество успешно и неуспешно отправленных.
    """
    from pydantic import BaseModel

    queue = _load_queue()
    if not queue:
        return 0, 0

    remaining: list[dict] = []
    sent = 0

    for entry in queue:
        try:
            from models.dynamic_crystal_data import create_dynamic_crystal_data_model
            data_dict = entry["data"]
            Model = create_dynamic_crystal_data_model(data_dict)
            model = Model.model_validate(data_dict)
            api_client.send_data(model)
            sent += 1
            logger.info("Отправлено из очереди: %s", entry.get("file_path"))
        except Exception as exc:
            logger.warning("Не удалось отправить из очереди: %s — %s", entry.get("file_path"), exc)
            remaining.append(entry)

    _save_queue(remaining)
    return sent, len(remaining)


def clear_queue() -> None:
    _save_queue([])


def get_queue_entries() -> list[dict[str, Any]]:
    return _load_queue()
