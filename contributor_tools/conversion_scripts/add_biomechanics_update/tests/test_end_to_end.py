from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from contributor_tools.conversion_scripts.add_biomechanics_update import convert


class DummyReader:
    def __init__(self):
        self._yielded = False

    def stream_frames(self):
        if not self._yielded:
            self._yielded = True
            yield pd.DataFrame(
                {
                    "dataset": ["Santos2017", "Santos2017"],
                    "subject": ["SUB01", "SUB01"],
                    "subject_mass": [70.0, 70.0],
                    "task_raw": ["standing", "standing"],
                    "time_s": [0.0, 0.01],
                    "grf_vertical_ipsi_N": [0.0, 120.0],
                    "grf_vertical_contra_N": [0.0, 130.0],
                    "hip_flexion_moment_contra_Nm": [5.0, 5.2],
                    "hip_flexion_moment_ipsi_Nm": [4.0, 4.1],
                }
            )
        else:
            return


@pytest.fixture(autouse=True)
def patch_reader(monkeypatch):
    monkeypatch.setattr(
        convert.b3d_reader,
        "B3DReader",
        lambda dataset_root, dataset_name, chunk_size: DummyReader(),
    )


def test_cli_writes_placeholder_files(tmp_path: Path, monkeypatch):
    # Patch writers to record calls instead of touching disk
    touched = {"time": False, "phase": False}

    def _mock_time_writer(df, events, output_root, dataset_name):
        touched["time"] = True

    def _mock_phase_writer(df, events, output_root, dataset_name):
        touched["phase"] = True

    monkeypatch.setattr(convert.writers, "write_time_chunk", _mock_time_writer)
    monkeypatch.setattr(convert.writers, "write_phase_chunk", _mock_phase_writer)

    args = [
        "--input-root",
        str(tmp_path / "input"),
        "--output-root",
        str(tmp_path / "output"),
        "--datasets",
        "Santos2017",
    ]
    (tmp_path / "input" / "Santos2017").mkdir(parents=True)

    convert.main(args)

    assert touched["time"]
    assert touched["phase"]
