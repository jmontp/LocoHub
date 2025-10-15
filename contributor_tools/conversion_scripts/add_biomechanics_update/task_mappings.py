"""Dataset-specific task metadata normalization for AddBiomechanics."""

from __future__ import annotations

import re
from typing import Callable, Dict

import pandas as pd

# Mapping from dataset name to normalization function. Each function should
# enforce canonical task labels, derive `task_id`, and populate a
# comma-separated `task_info` string following docs/reference/index.md.
_DATASET_HANDLERS: Dict[str, Callable[[pd.DataFrame], None]] = {}


def register(dataset_name: str):
    """Decorator registering a normalization function for a dataset."""

    def decorator(func: Callable[[pd.DataFrame], None]) -> Callable[[pd.DataFrame], None]:
        _DATASET_HANDLERS[dataset_name] = func
        return func

    return decorator


@register("Santos2017")
def _normalize_santos2017(df: pd.DataFrame) -> None:
    df["task"] = "standing_still"
    df["task_id"] = df.get("task_raw", "standing_still").astype(str).apply(_slugify)
    df["task_info"] = "variant:quiet_stance"


@register("Tiziana2019")
def _normalize_tiziana2019(df: pd.DataFrame) -> None:
    _fallback_handler(df)


def apply_task_metadata(df: pd.DataFrame, dataset_name: str) -> None:
    """Dispatch to the appropriate task normalization function."""

    handler = _DATASET_HANDLERS.get(dataset_name, _fallback_handler)
    handler(df)


def _fallback_handler(df: pd.DataFrame) -> None:
    raw = df.get("task_raw")
    if raw is None:
        df["task"] = "functional_task"
        df["task_id"] = "unspecified"
        df["task_info"] = "variant:unspecified"
        return

    slug = raw.astype(str).apply(_slugify)
    task_family = slug.apply(_infer_task_family)

    df["task"] = task_family
    df["task_id"] = slug.replace("", "unspecified")
    df["task_info"] = "variant:" + df["task_id"]


def _slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    value = value.strip("_")
    return value or "unspecified"


def _infer_task_family(slug: str) -> str:
    if not slug:
        return "functional_task"
    if "sit_to_stand" in slug:
        return "sit_to_stand"
    if "stand_to_sit" in slug:
        return "stand_to_sit"
    if "stair" in slug and "down" in slug:
        return "stair_descent"
    if "stair" in slug:
        return "stair_ascent"
    if "incline" in slug or "uphill" in slug:
        return "incline_walking"
    if "decline" in slug or "downhill" in slug:
        return "decline_walking"
    if "run" in slug:
        return "run"
    if "jump" in slug or "hop" in slug:
        return "jump"
    if "walk" in slug:
        return "level_walking"
    if "stand" in slug:
        return "standing_still"
    return "functional_task"
