"""Synthetic-only adapter built from the tracked historical converter fixture.

Execute the reviewed correction on that fixture, selecting only conversion
functions. All subject/task policy here is deliberately synthetic. No local
scientific artifacts, real source files, or heavy converter imports are used.
"""
import ast
from enum import Enum
import json
from pathlib import Path
from typing import Dict, Optional
import numpy as np
import pandas as pd
from contributor_tools.prepare_gt24_continuous_correction import patch

class SegmentationArchetype(Enum):
    GAIT='gait'
    OTHER='other'

TASK_ARCHETYPE_MAP={'level_walking':SegmentationArchetype.GAIT}
GRF_THRESHOLD_N=20.

def map_task_name(name):return 'level_walking','synthetic',{}
def get_collection_phase(*args):return 1
def get_exo_state(*args):return 'powered'
def is_day2_trial(*args):return False
def get_subject_mass(*args):return 70.

def load_trial_data(folder,subject,exo_state):
    return {kind:pd.read_csv(path) for kind in ('angle_filt','moment_filt','grf','velocity','insole_sim','moment_filt_bio','exo') if (path:=folder/f'{subject}_{folder.name}_{kind}.csv').exists()}

_baseline=Path(__file__).with_name('gt24_time_converter_baseline.py.txt')
_tree=ast.parse(patch(_baseline.read_text()))
_needed={'_gradient_over_time','_series_or_nan','_determine_reference_leg','process_trial_time'}
_functions=ast.Module(body=[node for node in _tree.body if isinstance(node,ast.FunctionDef) and node.name in _needed],type_ignores=[])
assert {node.name for node in _functions.body}==_needed
exec(compile(_functions,str(_baseline)+' [synthetic reviewed correction]','exec'),globals())
