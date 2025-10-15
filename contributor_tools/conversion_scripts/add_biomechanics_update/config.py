"""Configuration helpers for the AddBiomechanics update pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List


@dataclass(frozen=True)
class DatasetConfig:
    """Simple container storing dataset selection metadata."""

    dataset_names: List[str]


_DEFAULT_DATASETS = [
    "Santos2017",
    "Tiziana2019",
    "Moore2015",
    "Camargo2021",
    "Hamner2013",
]


def load_dataset_config(selected: Iterable[str] | None) -> DatasetConfig:
    """Return a dataset configuration after validating the requested names."""

    if selected:
        dataset_names = sorted(set(selected))
    else:
        dataset_names = list(_DEFAULT_DATASETS)
    return DatasetConfig(dataset_names=dataset_names)


def dataset_output_paths(output_root: Path, dataset_name: str) -> dict[str, Path]:
    """Return canonical output paths for time and phase files."""

    dataset_root = output_root / dataset_name
    return {
        "root": dataset_root,
        "time": dataset_root / f"{dataset_name.lower()}_time.parquet",
        "phase": dataset_root / f"{dataset_name.lower()}_phase.parquet",
    }


def ensure_output_layout(output_root: Path, dataset_name: str, *, overwrite: bool) -> None:
    """Create the dataset output directory and optionally clean existing exports."""

    paths = dataset_output_paths(output_root, dataset_name)
    paths["root"].mkdir(parents=True, exist_ok=True)
    if overwrite:
        for key in ("time", "phase"):
            if paths[key].exists():
                paths[key].unlink()
