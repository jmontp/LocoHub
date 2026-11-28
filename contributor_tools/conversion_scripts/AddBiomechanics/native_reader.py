"""Load the B3D extension without the optional Torch-based Python wrappers.

This shares dependency admission only, never source extraction or comparison.
Native initialization must still run inside the coordinator's memory/timeout guard.
"""
import importlib
import importlib.metadata
import sys

REQUIRED_METHODS = (
    'getTrialOriginalName', 'getTrialSplitIndex', 'getTrialNumProcessingPasses',
    'getTrialLength', 'getTrialTimestep', 'getTrialName', 'getNumTrials',
    'getMassKg', 'getNumProcessingPasses', 'getOpensimFileText',
    'getProcessingPassType', 'getContactBodies', 'readFrames',
)


def reject_torch():
    if any(name == 'torch' or name.startswith('torch.') for name in sys.modules):
        raise RuntimeError('Torch is loaded; refuse source-reader process')


def load_reader():
    reject_torch()
    try:
        native = importlib.import_module('nimblephysics_libs._nimblephysics')
    finally:
        reject_torch()
    subject = getattr(getattr(native, 'biomechanics', None), 'SubjectOnDisk', None)
    if not callable(subject):
        raise RuntimeError('Native SubjectOnDisk API is unavailable')
    missing = [name for name in REQUIRED_METHODS if not callable(getattr(subject, name, None))]
    if missing:
        raise RuntimeError('Native source reader lacks required APIs: ' + ', '.join(missing))
    version = importlib.metadata.version('nimblephysics')
    if not version:
        raise RuntimeError('Installed source-reader version unavailable')
    return native, version
