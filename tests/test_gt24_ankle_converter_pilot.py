"""Guard/admission fixtures only; no numerical workers or scientific arrays."""
import io
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch,Mock
from contributor_tools import run_gt24_ankle_converter_pilot as tool


class ConverterPilotTests(TestCase):
    def test_explicit_complete_recording_admission(self):
        self.assertLess(tool.admission_estimate(18*1024**2),768*1024**2)
        for size in [-1,24*1024**2,30*1024**2]:
            with self.assertRaises(MemoryError):tool.admission_estimate(size)

    def test_ten_targeted_coordinate_fields_no_assistance_or_segments(self):
        self.assertEqual(len(tool.FIELDS),10)
        self.assertEqual(len(set(tool.FIELDS.values())),10)
        self.assertFalse(any('assistance' in k or 'sagittal' in k for k in tool.FIELDS))
        self.assertEqual(tool.FIELDS['ankle_dorsiflexion_velocity_contra_rad_s'],'source_ankle_coordinate_derived_velocity_contra_rad_s')

    def test_startup_host_rejection_starts_no_process(self):
        with patch.object(tool,'windows_available_mib',return_value=2815),patch.object(tool.subprocess,'Popen') as spawn:
            with self.assertRaises(MemoryError):tool.guarded(['synthetic'],Path('/tmp'),io.StringIO())
            spawn.assert_not_called()

    def test_startup_wsl_rejection_starts_no_process(self):
        with patch.object(tool,'windows_available_mib',return_value=4096),patch.object(tool,'linux_available_mib',return_value=3583),patch.object(tool.subprocess,'Popen') as spawn:
            with self.assertRaises(MemoryError):tool.guarded(['synthetic'],Path('/tmp'),io.StringIO())
            spawn.assert_not_called()

    def test_runtime_reserve_only_terminates_owned_group(self):
        process=Mock(pid=12345);process.poll.return_value=None
        with patch.object(tool,'windows_available_mib',return_value=4096),patch.object(tool,'linux_available_mib',side_effect=[4096,1024]),patch.object(tool,'headroom'),patch.object(tool.subprocess,'Popen',return_value=process),patch.object(tool.os,'killpg') as kill:
            with self.assertRaises(MemoryError):tool.guarded(['synthetic'],Path('/tmp'),io.StringIO())
            kill.assert_called_once_with(12345,tool.signal.SIGTERM)
            process.wait.assert_called_once_with(timeout=5)
