"""Mocked host/process checks; never launch conversions or PowerShell."""
import subprocess
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from contributor_tools import run_gt25_coverage_pilot as pilot


class PilotGuardTests(unittest.TestCase):
    def test_baseline_change_rejected(self):
        bound={'path':'/baseline.json','manifest_sha256':'before','outputs':[]}
        with patch.object(pilot,'baseline_evidence',return_value={**bound,'manifest_sha256':'after'}):
            with self.assertRaises(ValueError):pilot.verify_bound_baseline(bound)

    def test_startup_refusal_never_launches(self):
        with patch.object(pilot,'windows_available_mib',return_value=3583), patch.object(pilot.subprocess,'Popen') as launch:
            with self.assertRaises(MemoryError):
                pilot.guarded_stage(['worker'],stdout=None,output_root=Path('/out'),storage_check=Mock())
            launch.assert_not_called()

    def test_runtime_host_refusal_only_terminates_own_group(self):
        process=Mock(pid=12345);process.poll.return_value=None
        with patch.object(pilot,'windows_available_mib',side_effect=[4000,2047]), \
             patch.object(pilot,'linux_available_mib',return_value=4000), \
             patch.object(pilot.subprocess,'Popen',return_value=process) as launch, \
             patch.object(pilot.os,'killpg') as kill:
            with self.assertRaises(MemoryError):
                pilot.guarded_stage(['worker'],stdout=None,output_root=Path('/out'),storage_check=Mock())
            kill.assert_called_once_with(12345,pilot.signal.SIGTERM)
            self.assertTrue(launch.call_args.kwargs['start_new_session'])
            self.assertEqual(launch.call_args.args[0],['ionice','-c3','worker'])

    def test_runtime_linux_refusal_terminates_group(self):
        process=Mock(pid=12345);process.poll.return_value=None
        with patch.object(pilot,'windows_available_mib',return_value=4000), \
             patch.object(pilot,'linux_available_mib',side_effect=[4000,2047]), \
             patch.object(pilot.subprocess,'Popen',return_value=process), patch.object(pilot.os,'killpg') as kill:
            with self.assertRaises(MemoryError):
                pilot.guarded_stage(['worker'],stdout=None,output_root=Path('/out'),storage_check=Mock())
            kill.assert_called_once_with(12345,pilot.signal.SIGTERM)

    def test_guard_escalates_only_own_group_after_grace_period(self):
        process=Mock(pid=12345);process.poll.return_value=None
        process.wait.side_effect=[subprocess.TimeoutExpired('worker',5),0]
        with patch.object(pilot,'windows_available_mib',side_effect=[4000,0]), \
             patch.object(pilot,'linux_available_mib',return_value=4000), \
             patch.object(pilot.subprocess,'Popen',return_value=process), patch.object(pilot.os,'killpg') as kill:
            with self.assertRaises(MemoryError):
                pilot.guarded_stage(['worker'],stdout=None,output_root=Path('/out'),storage_check=Mock())
            self.assertEqual([c.args for c in kill.call_args_list],[(12345,pilot.signal.SIGTERM),(12345,pilot.signal.SIGKILL)])

    def test_completed_process_is_not_killed(self):
        process=Mock(pid=12345,returncode=0);process.poll.return_value=0
        with patch.object(pilot,'windows_available_mib',return_value=4000), \
             patch.object(pilot,'linux_available_mib',return_value=4000), \
             patch.object(pilot.subprocess,'Popen',return_value=process), patch.object(pilot.os,'killpg') as kill:
            result=pilot.guarded_stage(['worker'],stdout=None,output_root=Path('/out'),storage_check=Mock())
            self.assertEqual(result.returncode,0);kill.assert_not_called()

    def test_timeout_terminates_only_owned_group(self):
        process=Mock(pid=12345);process.poll.return_value=None
        with patch.object(pilot,'windows_available_mib',return_value=4000), \
             patch.object(pilot,'linux_available_mib',return_value=4000), \
             patch.object(pilot.subprocess,'Popen',return_value=process), \
             patch.object(pilot.time,'monotonic',side_effect=[0,181]), patch.object(pilot.os,'killpg') as kill:
            with self.assertRaises(subprocess.TimeoutExpired):
                pilot.guarded_stage(['worker'],stdout=None,output_root=Path('/out'),storage_check=Mock())
            kill.assert_called_once_with(12345,pilot.signal.SIGTERM)

    def test_host_measurement_failure_fails_closed(self):
        process=Mock(pid=12345);process.poll.return_value=None
        with patch.object(pilot,'windows_available_mib',side_effect=[4000,RuntimeError('probe unavailable')]), \
             patch.object(pilot,'linux_available_mib',return_value=4000), \
             patch.object(pilot.subprocess,'Popen',return_value=process), patch.object(pilot.os,'killpg') as kill:
            with self.assertRaises(RuntimeError):
                pilot.guarded_stage(['worker'],stdout=None,output_root=Path('/out'),storage_check=Mock())
            kill.assert_called_once_with(12345,pilot.signal.SIGTERM)

    def test_runtime_storage_refusal_terminates_group(self):
        process=Mock(pid=12345);process.poll.return_value=None
        with patch.object(pilot,'windows_available_mib',return_value=4000), \
             patch.object(pilot,'linux_available_mib',return_value=4000), \
             patch.object(pilot.subprocess,'Popen',return_value=process), patch.object(pilot.os,'killpg') as kill:
            with self.assertRaises(OSError):
                pilot.guarded_stage(['worker'],stdout=None,output_root=Path('/out'),
                                    storage_check=Mock(side_effect=[None,OSError('disk reserve')]))
            kill.assert_called_once_with(12345,pilot.signal.SIGTERM)
