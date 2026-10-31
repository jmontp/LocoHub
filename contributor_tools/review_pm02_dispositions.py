"""PM-02: give every retained historical job, queue and watcher a current disposition.

Read-only. Every top-level directory under converted_datasets/reconversion_v2 is a
retained job record (each was written by a plan, launcher, pilot, audit or review), so
each gets a row unless it is the execution record of a queue job (FOLD). Every queue
plan, including retired plan versions, is expanded into its jobs. It reads small JSON receipts (4 MiB cap), hashes
small control files and checks recorded PIDs against the current Linux boot and a
read-only Windows process census. Writes docs/quality/audits/pm02-job-dispositions.json
and review_sheets/PM-02/. Starts, signals and resumes nothing; loads no scientific arrays.

Dispositions (current, not historical):
  completed_unreviewed      terminal success receipt, rehashed now; evidence only, not approval
  superseded                a named later job or result replaces it (chain must end elsewhere)
  needs_fresh_reviewed_plan work still in scope; owner task writes a new reviewed plan
  quarantined_known_bad     recipe known wrong; never rerun as defined
  obsolete                  no longer needed or no longer reproducible; closed here
"""
import os
for key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[key] = '1'
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from contributor_tools.common.review_sheet import page

V2 = ROOT / 'converted_datasets/reconversion_v2'
AUDITS = ROOT / 'docs/quality/audits'
OUT = AUDITS / 'pm02-job-dispositions.json'
SHEET = ROOT / 'review_sheets/PM-02'
BACKLOG = ROOT / 'docs/maintainers/backlog.json'
MAX_JSON = 4 * 1024**2
INPUTS = ['docs/quality/audits/backlog-refresh-20261027.json',
          'docs/quality/audits/queue-recovery-expanded-49-summary.json',
          'docs/quality/audits/mblue-complete-scope.json',
          'converted_datasets/reconversion_v2/mblue_priority_handoff_20261021/status.json',
          'docs/quality/audits/reconstruction-queue-recovery.json',
          'converted_datasets/reconversion_v2/swarm_backlog_20261021/gt25_stop_dependency_closure_replacement.json',
          'docs/quality/audits/pm01-stopped-jobs-review.json',
          'docs/quality/audits/pm01-um21-tread-pilot-handoff.json',
          'docs/maintainers/backlog.json']
DISPOSITIONS = ['completed_unreviewed', 'superseded', 'needs_fresh_reviewed_plan', 'quarantined_known_bad', 'obsolete']
NOT_SUCCESS = {'stopped', 'failed', 'never_launched', 'stale_running', 'no_terminal_record'}
PREPARED = re.compile(r'prepar|planned|not_run|not_executed|not_adopted|proposal|pending|waiting|draft|ready')
UNSUCCESSFUL = re.compile(r'fail|stopped|incomplete|not_started')
CONTROL_JSON = {'queue_status.json', 'status.json', 'batch_status.json', 'dispatch_status.json', 'batch_summary.json',
                'batch_plan.json', 'plan.json', 'execution_plan.json', 'launch.json', 'launch_receipt.json', 'handoff.json'}
RECEIPTS = ['pilot_summary.json', 'source_comparison.json', 'conversion_summary.json', 'planar_preservation_summary.json',
            'native_status.json', 'smoke_result.json', 'retrieval.json', 'window_verification.json', 'source_readback.json',
            'preparation_manifest.json', 'execution_handoff.json', 'attempt_failure.json']
SKIP_PY = re.compile(r'^(test_.*|converter_snapshot|smoke)\.py$')

# --- Current owner task: first matching rule on the job or directory name. -----------------
OWNER_RULES = [
    (r'^(memory_resume|memory_refusal|compression_handoff|ntfs_compression|gt23_ntfs|swarm_backlog)', 'PM-02'),
    (r'^adb_', 'ADB-P01'),
    (r'^fukuchi_browser', 'DOC-01'),
    (r'^fukuchi', 'FU18-P01'),
    (r'^gait120_(anthropometry|publisher_code_review|force_pilot)', 'GA26-C01'),
    (r'^gait120', 'GA26-F01'),
    (r'^gt21_ab17', 'GT21-A01'),
    (r'^gt21_(subjectinfo|subject_mass_review)', 'GT21-A02'),
    (r'^gt21_participant_repository', 'GT21-S01'),
    (r'^gt21_(force_geometry|levelground_force_geometry|ramp_force_geometry|stair_force_geometry|plate_geometry|geometry_sign|forward_axis|'
     r'levelground_contact|ramp_contact|stair_contact|force_fix|force_fixed|numeric_reader|levelground_conversion|ramp_conversion|'
     r'stair_conversion|treadmill_force_readback|all_completed_force)', 'GT21-C01'),
    (r'^gt21_(strict_owned_ramp|terrain_fix_ramp|combined_ramp_adoption)', 'GT21-P02'),
    (r'^gt21_(force_source_probe|levelground_force_probe|ramp_force_probe|stair_force_probe)', 'GT21-C01'),
    (r'^gt21_(bilateral|strict|combined_(levelground|treadmill|proposal))', 'GT21-P01'),
    (r'^gt21_(terrain|stair|combined_(ramp|stair))', 'GT21-P02'),
    (r'^gt21', 'GT21-F01'),
    (r'^gt23_(force|known_pose|cop)', 'GT23-C01'),
    (r'^gt23', 'GT23-F01'),
    (r'^gt24_(source_companion|companion)', 'GT24-S01'),
    (r'^gt24_(invalid_torque|ankle_adoption|phase3|phase1and2|ankle_convention|gt25_source_units|source_mass_coverage)', 'GT24-C01'),
    (r'^gt24_(duplicate_interval|unique_intervals)', 'GT24-S01'),
    (r'^gt24', 'GT24-P01'),
    (r'^gt25_author_(event|code)', 'GT25-E01'),
    (r'^gt25_(full_2026|ankle_sign_proposal|ankle_normalization_proposal|explicit_newton|units_primary|coverage|identity_pilot|source_pilot)', 'GT25-C01'),
    (r'^gt25_selected_full', 'GT25-F01'),
    (r'^gt25(_(shuffle|recovered_admission|unchanged|batch_smoke.*))?$', 'GT25-C01'),
    (r'^gt25', 'GT25-P01'),
    (r'^mblue_(fileinfo|native_fileinfo|modelpose|native_pose|pose_station|station_pose|marker_endpoint)', 'MB24-C01'),
    (r'^mblue', 'MB24-F01'),
    (r'^strokepig', 'SP50-F01'),
    (r'^um21_ankle', 'UM21-C01'),
    (r'^um21_(pelvis_correspondence|correspondence)', 'UM21-C02'),
    (r'^um21_.*(planar|boundar|curated_window)', 'UM21-B01'),
    (r'^um21_tread_components_pilot', 'UM21-T02'),
    (r'^um21_tread_(full_curation|full_readback|pilot_2026|corrected)', 'UM21-T01'),
    (r'^um21_normalized_transfers', 'UM21-X01'),
    (r'^um21_tread$', 'UM21-T01'),
    (r'^um21_tread', 'UM21-T03'),
    (r'^um21_stair', 'UM21-S01'),
    (r'^um21_wtr', 'UM21-W01'),
    (r'^um21_running', 'UM21-X01'),
    (r'^um24k', 'UM24K-F01'),
]
DATASET = [(r'^um21', 'UMich 2021'), (r'^gt21', 'GaTech 2021'), (r'^gt23', 'GaTech 2023'), (r'^gt24', 'GaTech 2024'),
           (r'^gt25', 'GaTech 2025'), (r'^mblue', 'MBLUE'), (r'^gait120', 'Gait120'), (r'^strokepig', 'StrokePiG'),
           (r'^fukuchi', 'Fukuchi 2018'), (r'^um24k', 'UMich 2024 knee exo'), (r'^adb', 'AddBiomechanics')]

# --- Lineage groups: ordered oldest to newest; the last member is the head. -----------------
# Non-head members that did not complete are superseded by the head. Completed members keep
# their own result unless an explicit override says a later result replaced them.
D = '_20261021'
GROUPS = {
    'gt25_ankle_normalization': ['gt25_ankle_v3_after_gt23', 'gt25_ankle_pilot_handoff_v3', 'gt25_normalization_pilot_handoff_v4',
                                 'gt25_normalization_v4_after_gt23', 'gt25_four_family_pilot_v5', 'gt25_four_family_pilot_v5_preparation_v2',
                                 'gt25_four_family_pilot_v5_preparation_v3', 'gt25_v5_four_family_after_boundary'],
    'gt25_selected_full': ['gt25_selected_full_v4_preparation', 'gt25_selected_full_v4_preparation_v2', 'gt25_selected_full_v4_preparation_v3',
                           'gt25_selected_full_v5', 'gt25_selected_full_v5_preparation_v2', 'gt25_selected_full_v5_preparation_v3'],
    'gt25_streaming_transfer': ['gt25_streaming_transfer_pilot', 'gt25_streaming_transfer_pilot_v2', 'gt25_streaming_transfer_pilot_v3',
                                'gt25_streaming_transfer_pilot_v4'],
    'gt25_source_companion': ['gt25_source_companion_threeclass_pilot', 'gt25_source_companion_threeclass_pilot_v2',
                              'gt25_source_companion_after_ab03'],
    'gt25_author_members': ['gt25_author_event_members', 'gt25_author_event_members_v2', 'gt25_author_event_members_v3',
                            'gt25_author_event_members_v4'],
    'gt25_author_events': ['gt25_author_event_clock_pilot', 'gt25_author_events_after_stair'],
    'um21_running_planar': ['um21_running_planar_preserved', 'um21_running_planar_recovered_full', 'um21_running_planar_after_strokepig'],
    'um21_boundary': ['um21_boundary_scope_pilot', 'um21_boundary_scope_pilot_v2', 'um21_boundary_source_recovered_pilot',
                      'um21_boundary_recovery_after_running'],
    'um21_planar': ['um21_tread_planar_restored', 'um21_stairs_planar_restored', 'um21_planar_after_gait120'],
    'um21_tread_components': ['um21_tread_components_restored', 'um21_tread_components_after_gt23'],
    'um21_stairs': ['um21_stairs_restored', 'um21_stairs_restored_v2', 'um21_stairs_after_gt24'],
    'um21_wtr': ['um21_wtr_restored', 'um21_wtr_restored_v2', 'um21_wtr_after_stairs'],
    'um21_pelvis': ['um21_pelvis_correspondence_pilot', 'um21_correspondence_after_ab17'],
    'um21_ankle': ['um21_ankle_after_gt25', 'um21_ankle_after_mblue_v2', 'um21_ankle_after_mblue_retry3'],
    'mblue_fileinfo': ['mblue_fileinfo_metadata_plan', 'mblue_fileinfo_metadata_early', 'mblue_fileinfo_early_detour',
                       'mblue_native_fileinfo_pilot', 'mblue_native_fileinfo_after_gt24'],
    'mblue_pose': ['mblue_modelpose_pilot', 'mblue_modelpose_pilot_v2', 'mblue_station_pose_check_v1', 'mblue_pose_station_after_gt21'],
    'adb': ['adb_tiziana_subject29_source_pilot', 'adb_tiziana_subject29_source_pilot_v2', 'adb_tiziana_single_pilot',
            'adb_pilot_after_mblue_pose'],
    'gt23_force': ['gt23_cop_chain_preparation', 'gt23_force_after_um21', 'gt23_force_cop_after_um21_v2', 'gt23_force_cop_after_um21_retry3'],
    'gt23_known_pose': ['gt23_known_pose_native_pilot', 'gt23_known_pose_after_author_events'],
    'fukuchi_first_pair': ['fukuchi_first_pair_after_fileinfo', 'fukuchi_first_pair_after_fileinfo_v2'],
    'fukuchi_browser': ['fukuchi_browser_detour', 'fukuchi_browser_detour_v2', 'fukuchi_browser_detour_v3'],
    'fukuchi_preview': ['fukuchi_preview_detour', 'fukuchi_preview_v2_detour'],
    'gt24_unknown_mass': ['gt24_unknown_mass_pilot', 'gt24_unknown_mass_after_tread_draft', 'gt24_unknown_mass_after_tread'],
    'gt24_mass': ['gt24_participant_mass_pilot', 'gt24_participant_mass_pilot_v2', 'gt24_participant_mass_pilot_v3',
                  'gt24_mass_v3_after_gt25_v4'],
    'gt24_membership': ['gt24_complete_membership', 'gt24_complete_membership_v2'],
    'gt24_equivalence': ['gt24_streaming_equivalence', 'gt24_streaming_equivalence_v2', 'gt24_equivalence_after_gt23'],
    'gt24_continuous': ['gt24_continuous_pilot', 'gt24_continuous_detour', 'gt24_continuous_pilot_v2', 'gt24_continuous_v2_detour'],
    'gt24_ankle_converter': ['gt24_ankle_converter_pilot', 'gt24_ankle_converter_pilot_v2'],
    'gt21_ab17': ['gt21_ab17_restoration', 'gt21_ab17_restoration_v2', 'gt21_ab17_restoration_v3', 'gt21_ab17_restoration_v4',
                  'gt21_ab17_after_gt23_pose'],
    'gt21_subjectinfo': ['gt21_subjectinfo_metadata_pilot', 'gt21_subjectinfo_after_um21'],
    'gt21_strict': ['gt21_strict_pilot_runners', 'gt21_strict_after_gt24companion'],
    'gt21_stair': ['gt21_terrain_combined_runner', 'gt21_stair_baseline_strict_preparation', 'gt21_stair_after_adb'],
    'gait120_baseline': ['gait120_source_checked_full', 'gait120_source_checked_full_v2', 'gait120_source_checked_full_v3',
                         'gait120_source_checked_full_v4', 'gait120_full_after_um21_wtr'],
    'gait120_derivatives': ['gait120_corrected_derivatives_full', 'gait120_corrected_derivatives_full_v2',
                            'gait120_corrected_derivatives_full_v3', 'gait120_corrected_after_gt25_companion'],
    'um24k_s1': ['um24k_ensemble_restoration_preparation', 'um24k_ensemble_restoration_preparation_v2', 'um24k_s1_after_gt24_raw'],
    'um24k_s2': ['um24k_s2_restoration_preparation', 'um24k_s2_after_s1'],
    'strokepig_native': ['strokepig_native_full', 'strokepig_native_after_fukuchi'],
    'gt21_batches': ['gt21_native_corrected', 'gt21_metadata_corrected'],
    'mblue_normalized': ['mblue_full_normalized', 'mblue_full_normalized_v2'],
    'gt21_force_probe': ['gt21_force_source_probe', 'gt21_force_source_probe_1536'],
}
GROUPS = {g: [m if m.endswith('_20261020') else m + D for m in members] for g, members in GROUPS.items()}

# Dirs that are the execution record of a queue job; folded into that job's row.
FOLD = {'gt21_memory_wait_20261021': 'metadata_serial_queue_20261021/0:gt21',
        'gt21_force_corrected_full_20261021': 'metadata_serial_queue_20261021/0:gt21',
        'gt21_native_corrected_20261021': 'corrected_serial_queue_20261021/1:gt21',
        'gt24_phase3_corrected_20261020': 'fixed_data_queue_20261020/1:gt24_phase3',
        'gt24_phase3_corrected_9g_20261020': 'fixed_data_queue_9g_20261020/0:gt24_phase3',
        'gt24_phase3_canonical_20261020': 'fixed_data_queue_canonical_20261020/0:gt24_phase3',
        'gt24_phase3_timing_20261020': 'fixed_data_queue_timing_20261020/0:gt24_phase3'}
# Executed through a detour whose exit code is the only process receipt.
EXECUTED_BY = {'gt24_continuous_pilot_20261021': 'gt24_continuous_detour_20261021',
               'mblue_fileinfo_metadata_early_20261021': 'mblue_fileinfo_early_detour_20261021',
               'gt24_native_parsed_ankle_pilot_20261021': 'gt24_native_ankle_detour_20261021',
               'gt24_ankle_converter_pilot_v2_20261021': 'gt24_converter_detour_20261021',
               'gt24_continuous_pilot_v2_20261021': 'gt24_continuous_v2_detour_20261021',
               'gt25_streaming_transfer_pilot_v2_20261021': 'gt25_streaming_transfer_detour_20261021',
               'mblue_planar_preserved_early_full_20261021': 'mblue_planar_early_detour_20261021'}

Q = '_serial_queue_20261021/'
MB_DETOUR = 'mblue_priority_handoff_20261021'
# Explicit dispositions: (disposition, successor or None, owner or None, note).
OVERRIDES = {
    # GT25 ankle-sign stop: the original converter and its correction pilots are known wrong.
    'gt25' + Q + '0:gt25': ('quarantined_known_bad', None, 'GT25-C01', 'Plantarflexion-positive source mapped as dorsiflexion; later source review also found unsupported normalization assumptions.'),
    'correction_pilot' + Q + '0:gt25_shuffle': ('quarantined_known_bad', None, 'GT25-C01', 'Same GT25 ankle-sign recipe.'),
    'correction_pilot' + Q + '1:gt25_recovered_admission': ('quarantined_known_bad', None, 'GT25-C01', 'Same GT25 ankle-sign recipe.'),
    'correction_pilot' + Q + '2:gt25_unchanged': ('quarantined_known_bad', None, 'GT25-C01', 'Same GT25 ankle-sign recipe.'),
    'gt25_batch_smoke_20261021': ('quarantined_known_bad', None, 'GT25-C01', 'Smoke output predates the ankle-sign stop and its receipt has no code binding; treated as produced by the stopped converter.'),
    # StrokePiG is unrelated to the GT25 error: restored as its own job.
    'gt25' + Q + '1:strokepig_native': ('superseded', 'strokepig_native_after_fukuchi_20261021', 'SP50-F01', 'Restored as an independent StrokePiG job; SP50-F01 does not depend on any GT25 task.'),
    # GT24 mass normalization error.
    'gt24_torque' + Q + '0:gt24_invalid_torque_outputs': ('quarantined_known_bad', None, 'GT24-C01', 'Pending mass-lookup fix and a new plan.'),
    'gt24_phase_ankle_adoption' + Q + '0:gt24_ankle_adoption_prepare': ('quarantined_known_bad', None, 'GT24-C01', 'Pending mass-lookup fix and a new plan.'),
    'gt24_phase_ankle_adoption' + Q + '1:gt24_ankle_adoption_run': ('quarantined_known_bad', None, 'GT24-C01', 'Pending mass-lookup fix and a new plan.'),
    'metadata' + Q + '2:gt24_phase3': ('quarantined_known_bad', None, 'GT24-C01', 'Parent held because this recipe retains incorrect mass normalization.'),
    'metadata' + Q + '3:gt24_phase1and2': ('quarantined_known_bad', None, 'GT24-C01', 'Parent held because this recipe retains incorrect mass normalization.'),
    'metadata' + Q + '5:gt23': ('quarantined_known_bad', None, 'GT23-F01', 'Publisher moments are Nm mislabeled Nm/kg and AB03 mass conflicts (publisher 113.5 vs local 82.18 kg).'),
    # Original queue jobs replaced by later watchers or verified detours.
    'um21_boundary' + Q + '0:um21_curated_boundaries': ('superseded', 'um21_boundary_recovery_after_running_20261021', None, ''),
    'gt21_bilateral' + Q + '0:gt21_bilateral_levelground': ('superseded', 'gt21_strict_after_gt24companion_20261021', None, ''),
    'gt21_bilateral' + Q + '1:gt21_bilateral_treadmill': ('superseded', 'gt21_strict_after_gt24companion_20261021', None, ''),
    'gt21_force' + Q + '0:gt21_full_force_readback': ('needs_fresh_reviewed_plan', None, 'GT21-F01', 'Requires the full corrected 2,301-record batch, which stopped at 102.'),
    'gt21_events' + Q + '0:gt21_full_event_terrain_review': ('needs_fresh_reviewed_plan', None, 'GT21-F01', 'Requires the full corrected batch.'),
    'gt21_terrain' + Q + '0:gt21_terrain_ramp_pilot': ('superseded', 'gt21_strict_after_gt24companion_20261021', 'GT21-P02', 'Ramp mode moved into the strict three-mode pilot.'),
    'gt21_terrain' + Q + '1:gt21_terrain_stair_pilot': ('superseded', 'gt21_stair_after_adb_20261021', None, ''),
    'mblue_pelvis' + Q + '0:mblue_pelvis_rebuild': ('superseded', MB_DETOUR, None, 'Completed by the priority detour; summary rehashed.'),
    'mblue_pelvis' + Q + '1:mblue_pelvis_readback': ('superseded', MB_DETOUR, None, 'Completed by the priority detour; summary rehashed.'),
    'mblue_pelvis' + Q + '2:mblue_pelvis_preservation': ('superseded', MB_DETOUR, None, 'Completed by the priority detour; summary rehashed.'),
    'mblue_stair_reference' + Q + '0:mblue_stair_reference_correction': ('superseded', MB_DETOUR, None, 'Completed by the priority detour; summary rehashed.'),
    'correction_pilot' + Q + '3:gt21_combined_levelground': ('superseded', 'gt21_strict_after_gt24companion_20261021', None, ''),
    'correction_pilot' + Q + '4:gt21_combined_treadmill': ('superseded', 'gt21_strict_after_gt24companion_20261021', None, ''),
    'gt21_terrain_adoption' + Q + '0:gt21_combined_ramp': ('superseded', 'gt21_strict_after_gt24companion_20261021', 'GT21-P02', 'Ramp mode moved into the strict three-mode pilot.'),
    'gt21_terrain_adoption' + Q + '1:gt21_combined_stair': ('superseded', 'gt21_stair_after_adb_20261021', None, ''),
    'mblue_planar' + Q + '0:mblue_planar_preservation': ('superseded', 'mblue_planar_early_detour_20261021', None, 'Completed by the early planar detour (335 blocks, 15,061 observations).'),
    'fukuchi_ensemble' + Q + '0:fukuchi_ensemble_pilot': ('superseded', 'fukuchi_early_detour_20261021', None, ''),
    'um21_running_planar' + Q + '0:um21_running_planar_preservation': ('superseded', 'um21_running_planar_after_strokepig_20261021', None, ''),
    'mblue_fileinfo' + Q + '0:mblue_fileinfo_metadata': ('superseded', 'mblue_native_fileinfo_after_gt24_20261021', None, ''),
    'mblue_modelpose' + Q + '0:mblue_native_pose': ('superseded', 'mblue_pose_station_after_gt21_20261021', None, ''),
    'metadata' + Q + '0:gt21': ('needs_fresh_reviewed_plan', None, 'GT21-F01', 'Native worker failed deterministically at AB06 stair_1_l_01_02 (unknown stair pattern, NoObservations assert); 102/2,301 produced. Needs a source-backed mapping or recorded exclusion for that pattern first.'),
    'metadata' + Q + '1:um21_tread_components': ('superseded', 'um21_tread_components_after_gt23_20261021', None, ''),
    'metadata' + Q + '4:gait120': ('superseded', 'gait120_full_after_um21_wtr_20261021', None, ''),
    'um21_stair' + Q + '0:um21_stairs': ('superseded', 'um21_stairs_after_gt24_20261021', None, ''),
    'um21_stair' + Q + '1:um21_stairs_readback': ('superseded', 'um21_stairs_after_gt24_20261021', None, ''),
    'um21_wtr' + Q + '0:um21_wtr': ('superseded', 'um21_wtr_after_stairs_20261021', None, ''),
    'um21_wtr' + Q + '1:um21_wtr_readback': ('superseded', 'um21_wtr_after_stairs_20261021', None, ''),
    'corrected' + Q + '1:gt21': ('superseded', 'gt21_metadata_corrected_20261021', 'GT21-F01', 'Native batch stopped by request at 16/2,301.'),
    'corrected' + Q + '2:gt24_phase3': ('superseded', 'metadata' + Q + '2:gt24_phase3', None, 'Never started; same job re-queued.'),
    'corrected' + Q + '3:gt24_phase1and2': ('superseded', 'metadata' + Q + '3:gt24_phase1and2', None, 'Never started; same job re-queued.'),
    'corrected' + Q + '4:gait120': ('superseded', 'metadata' + Q + '4:gait120', None, 'Never started; same job re-queued.'),
    'corrected' + Q + '5:gt23': ('superseded', 'metadata' + Q + '5:gt23', None, 'Never started; same job re-queued.'),
    'gt21_metadata_corrected_20261021': ('superseded', 'metadata' + Q + '0:gt21', 'GT21-F01', 'Native worker failed at 36/2,301; the force-corrected batch replaced it.'),
    'fixed_data_queue_20261020/1:gt24_phase3': ('superseded', 'fixed_data_queue_9g_20261020/0:gt24_phase3', None, 'Exit 2 at 50/752.'),
    'fixed_data_queue_9g_20261020/0:gt24_phase3': ('superseded', 'fixed_data_queue_canonical_20261020/0:gt24_phase3', None, 'Exit 2 at 75/752.'),
    'fixed_data_queue_canonical_20261020/0:gt24_phase3': ('superseded', 'fixed_data_queue_timing_20261020/0:gt24_phase3', None, 'Stopped by request at 33/752.'),
    'fixed_data_queue_timing_20261020/0:gt24_phase3': ('superseded', 'metadata' + Q + '2:gt24_phase3', None, 'Exit 2 at 484/752; same phase-3 recipe later quarantined.'),
    'gt21_native_batch_20261020': ('superseded', 'corrected' + Q + '1:gt21', None, 'Dispatcher never started (predecessor incomplete).'),
    'gait120_full_batch_20261020': ('superseded', 'metadata' + Q + '4:gait120', None, 'Dispatcher never started (predecessor incomplete).'),
    'gt23_full_native_batch_20261020': ('superseded', 'metadata' + Q + '5:gt23', None, 'Dispatcher never started (predecessor incomplete).'),
    'mblue_full_normalized_v2_20261021': ('superseded', MB_DETOUR, None, 'Completed result later replaced by the pelvis-corrected rebuild.'),
    'gt25_audit_after_mblue_20261021': ('needs_fresh_reviewed_plan', None, 'GT25-P01', 'Independent source audit of the streaming-transfer pilot never ran (STOP before follow-up).'),
    'gt23_publisher_after_gt25_v5_20261021': ('needs_fresh_reviewed_plan', None, 'GT23-F01', ''),
    # Results that ran from a temporary script that no longer exists.
    'fukuchi_browser_detour_v2_20261021': ('obsolete', None, 'DOC-01', 'Browser check ran a temporary script that no longer exists; not reproducible. Current UI checks belong to DOC-01.'),
    'fukuchi_browser_detour_v3_20261021': ('obsolete', None, 'DOC-01', 'Browser check ran a temporary script that no longer exists; not reproducible. Current UI checks belong to DOC-01.'),
    'mblue_fileinfo_probe_detour_20261021': ('obsolete', None, 'MB24-C01', 'Probe ran a temporary script that no longer exists; its finding fed the native FileInfo path.'),
    # Operations that are no longer needed.
    'memory_resume_20261021': ('obsolete', None, 'PM-02', 'Resumed the 20 Oct queues; every queue it resumed is now stopped.'),
    'memory_refusal_handoff_20261021': ('obsolete', None, 'PM-02', 'Record of queues restarted with a memory wait; all those queues are stopped.'),
    'compression_handoff_20261021': ('obsolete', None, 'PM-02', 'Storage-headroom coordination; S: now has ample free space.'),
    'ntfs_compression_runner_pilot_20261021': ('obsolete', None, 'PM-02', 'Storage-headroom pilot.'),
    'gt23_ntfs_compressed_20261021': ('obsolete', None, 'PM-02', 'Reached its storage target; no further work.'),
    'ntfs_compression_pilot_20261021': ('obsolete', None, 'PM-02', 'Storage-headroom pilot.'),
    'swarm_backlog_20261021': ('obsolete', None, 'PM-02', 'Planning snapshot of 21 Oct; the versioned backlog is now the plan of record. Its handoff files stay readable as references for owner tasks.'),
    'strokepig': ('superseded', 'strokepig_native_batch_smoke_20261021', 'SP50-F01', 'Input staging (TVC03/BWA6) for the one-record native smoke.'),
    'gt25_coverage_proposal_20261021': ('needs_fresh_reviewed_plan', None, 'GT25-C01', 'Inventory review completed, but its six pilot plans were never run.'),
    'mblue_pelvis_failure_review_20261021': ('superseded', MB_DETOUR, 'MB24-F01', 'Failed pelvis review; the pelvis-corrected rebuild in the priority detour replaced it.'),
    'um21_tread_pilot_20261020': ('superseded', 'um21_tread_corrected_20261020', 'UM21-T01', 'Earlier treadmill pilot; the corrected 50-recording baseline replaced it.'),
    'gt25_full_20261021': ('quarantined_known_bad', None, 'GT25-C01', 'Output root of the original GT25 batch stopped for the ankle-sign error.'),
    'metadata' + Q + 'retired:gt21_force_probe': ('superseded', 'gt21_force_source_probe_1536_20261021', 'GT21-C01', 'Listed only in retired plan versions; the probe was later completed under the 1536 MiB execution plan.'),
    **{f'um21_boundary_scope{Q}{i}:{j}': ('superseded', 'um21_boundary_recovery_after_running_20261021', 'UM21-B01', '')
       for i, j in enumerate(['boundary_fivecycle_source_pilot', 'boundary_full_scope_prepare', 'boundary_full_source_gate',
                              'boundary_planar_prepare', 'boundary_planar_run'])},
    **{f'um21_tread_stair_planar{Q}{i}:{j}': ('superseded', 'um21_planar_after_gait120_20261021', 'UM21-B01', 'Planar preservation for the 453 treadmill and stair records moved into one later job.')
       for i, j in enumerate(['tread_components_scope', 'tread_components_plan', 'tread_components_preserve',
                              'stairs_scope', 'stairs_plan', 'stairs_preserve'])},
}
OUTCOME_OVERRIDES = {  # receipts that are logs rather than JSON status files
    'gt21_ab17_acquisition_20261021': ('completed', 'publisher archive downloaded and SHA256 verified, not extracted (download.log)', 'download.log'),
}
NOTES = {
    'gt25_streaming_transfer_detour_20261021': 'Result predates the GT25 ankle-sign stop and its independent source audit never ran; GT25-P01 must check both.',
    'gt25_streaming_transfer_pilot_v2_20261021': 'Result predates the GT25 ankle-sign stop and its independent source audit never ran; GT25-P01 must check both.',
    'strokepig_serial_20261020': 'Covers 46 of the 151 native StrokePiG sources; it does not satisfy SP50-F01.',
    'strokepig_native_batch_smoke_20261021': 'Limited scope: one requested record of 151 (partial_requested_limit); not the native batch.',
    'fixed_data_queue_20261020/0:um21_tread': 'Limited scope: complete_partial_scope covers the 50 available treadmill recordings and the then-converted signals only.',
    'gt21_force_corrected_full_audit_v2_20261021': 'Covers 39 of 2,301 recordings.',
    'gt21_memory_wait_20261021/attempt_1792594489842444408/source_audit': 'Covers only the 102 produced recordings; not corrected-output approval.',
}


def sha(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def read_json(path):
    with Path(path).open('rb') as f:
        raw = f.read(MAX_JSON + 1)
    if len(raw) > MAX_JSON:
        return None
    return json.loads(raw)


def rel(path):
    return str(Path(path).resolve().relative_to(ROOT))


def owner_of(name):
    for pattern, task in OWNER_RULES:
        if re.search(pattern, name):
            return task
    return None


def dataset_of(name, kind):
    if kind == 'queue' or name.startswith(('memory_', 'compression_', 'ntfs_', 'gt23_ntfs')):
        return 'Orchestration'
    for pattern, label in DATASET:
        if re.search(pattern, name):
            return label
    return 'Orchestration'


def is_job_dir(d):
    """Every retained directory is a job record; kept as a function so the rule is explicit."""
    return d.is_dir()


def control_files(d):
    out = {}
    for p in sorted(d.iterdir()):
        if p.is_file() and (p.name in CONTROL_JSON or p.name in RECEIPTS or p.suffix == '.py' or p.name in ('watcher.log', 'pilot.log', 'download.log')):
            size = p.stat().st_size
            out[rel(p)] = sha(p) if size <= MAX_JSON else f'not hashed: {size} bytes'
        elif p.is_file() and p.suffix == '.json' and p.stat().st_size <= MAX_JSON:
            out[rel(p)] = sha(p)
    return out


def classify(name, d):
    """Return (outcome, status string, pids, receipt) from receipts in d."""
    if name in OUTCOME_OVERRIDES:
        outcome, status, receipt = OUTCOME_OVERRIDES[name]
        return outcome, status, [], rel(d / receipt)
    files = {p.name for p in d.iterdir()}
    for receipt in ('queue_status.json', 'status.json', 'batch_status.json', 'dispatch_status.json'):
        if receipt in files:
            s = read_json(d / receipt) or {}
            status = s.get('status', '')
            pids = [s['pid']] if isinstance(s.get('pid'), int) else []
            exit_code = s.get('exit_code')
            reason = s.get('reason', '')
            if status == 'pilot_finished_unreviewed':
                outcome = 'completed' if exit_code == 0 else 'failed'
            elif status in ('running', 'resumed_with_guards'):
                outcome = 'stale_running'
            elif status.startswith('not_started'):
                outcome = 'never_launched'
            elif status.startswith('stopped'):
                outcome = 'failed' if ('worker failed' in reason or 'not a proven pre-launch' in reason) else 'stopped'
            else:
                outcome = 'completed'
            return outcome, f'{status}' + (f' (exit {exit_code})' if exit_code is not None else '') + (f'; {reason}' if reason else ''), pids, rel(d / receipt)
    if 'batch_summary.json' in files:
        s = read_json(d / 'batch_summary.json')
        bs = s.get('batch_status')
        done = s.get('completed_recordings') == s.get('planned_recordings')
        outcome = 'stopped' if bs and bs.startswith('stopped') else ('completed' if done else 'stopped')
        return outcome, f"{bs or 'complete'} {s.get('completed_recordings')}/{s.get('planned_recordings')}", [], rel(d / 'batch_summary.json')
    if 'launch.json' in files:
        s = read_json(d / 'launch.json')
        if (d / 'watcher.log').exists() and 'Stopped before follow-up' in (d / 'watcher.log').read_text(errors='replace')[:4096]:
            return 'stopped', f"{s.get('status')}; STOP before follow-up", [s['pid']] if isinstance(s.get('pid'), int) else [], rel(d / 'watcher.log')
        if s.get('status') == 'prepared_not_executed':
            return 'never_launched', 'prepared_not_executed', [], rel(d / 'launch.json')
    found = []
    for receipt in RECEIPTS:
        if receipt in files:
            s = read_json(d / receipt)
            status = s.get('status') if isinstance(s, dict) else None
            found.append((receipt, status))
    for receipt, status in found:
        if receipt == 'native_status.json':
            if status == 'completed':
                return 'completed', 'native completed', [], rel(d / receipt)
            return 'failed', f'native {status}', [], rel(d / receipt)
    ran = [(r, st) for r, st in found if r not in ('preparation_manifest.json', 'execution_handoff.json', 'attempt_failure.json')]
    for receipt, status in ran:
        if status and not re.search(r'stopped|fail|not_started|incomplete', status):
            return 'completed', status, [], rel(d / receipt)
    for receipt, status in ran:
        if status:
            return ('failed' if 'fail' in status else 'stopped'), status, [], rel(d / receipt)
    if any(r == 'attempt_failure.json' for r, _ in found):
        return 'failed', 'attempt_failure', [], rel(d / 'attempt_failure.json')
    if ran and not any(n in files for n in ('native_status.json', 'audit_status.json')):
        # outputs exist but no receipt states a terminal status: not evidence of success
        return 'no_terminal_record', 'ran; no terminal status recorded', [], rel(d / ran[0][0])
    if 'handoff.json' in files:
        s = read_json(d / 'handoff.json') or {}
        return 'never_launched', s.get('status', 'handoff only'), [], rel(d / 'handoff.json')
    for receipt in ('native_status.json', 'audit_status.json'):
        if receipt in files:
            s = read_json(d / receipt) or {}
            st = str(s.get('status'))
            pids = [s['pid']] if isinstance(s.get('pid'), int) else []
            outcome = 'completed' if st in ('completed',) or st.startswith('checked') else ('failed' if 'fail' in st else 'stopped')
            return outcome, f'{receipt[:-5]} {st}', pids, rel(d / receipt)
    statuses = []
    for p in sorted(d.iterdir()):
        if p.is_file() and p.suffix == '.json' and p.stat().st_size <= MAX_JSON:
            try:
                s = read_json(p)
            except ValueError:
                continue
            if isinstance(s, dict) and isinstance(s.get('status'), str):
                planlike = bool(re.search(r'plan|proposal|preparation|handoff', p.name))
                statuses.append((p, s['status'], planlike, s.get('pid') if isinstance(s.get('pid'), int) else None))
    pids = sorted({x[3] for x in statuses if x[3]})
    done = [x for x in statuses if not x[2] and not UNSUCCESSFUL.search(x[1]) and not PREPARED.search(x[1])]
    if done:
        return 'completed', done[0][1], pids, rel(done[0][0])
    for word, outcome in (('stopped|incomplete|not_started', 'stopped'), ('fail', 'failed')):
        hit = [x for x in statuses if not x[2] and re.search(word, x[1])]
        if hit:
            return outcome, hit[0][1], pids, rel(hit[0][0])
    if statuses:
        return 'never_launched', statuses[0][1], pids, rel(statuses[0][0])
    if any(p.name.endswith('.json') and re.search(r'plan', p.name) for p in d.iterdir()):
        return 'never_launched', 'prepared plan without status', [], None
    return 'no_terminal_record', 'no status, plan or terminal receipt in this directory', [], None


def proc_identity(pid):
    p = Path(f'/proc/{pid}')
    if not p.exists():
        return None
    try:
        return (p / 'cmdline').read_bytes().replace(b'\0', b' ').decode(errors='replace')[:300]
    except OSError:
        return None


def windows_census():
    cmd = ['powershell.exe', '-NoProfile', '-Command',
           "Get-CimInstance Win32_Process | Where-Object { $_.Name -match 'matlab|python|opensim|MathWorks' } | "
           "Select-Object ProcessId,Name | ConvertTo-Json -Compress"]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=90, cwd='/tmp').stdout.strip()
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {'checked': False, 'error': str(exc)}
    rows = json.loads(out) if out else []
    rows = [rows] if isinstance(rows, dict) else rows
    workers = [r for r in rows if not r['Name'].startswith('MathWorks')]
    return {'checked': True, 'checked_at_utc': datetime.now(timezone.utc).isoformat(timespec='seconds'),
            'matching_processes': rows, 'matlab_python_opensim_workers': workers}


def build():
    backlog = read_json(BACKLOG)
    task_ids = {t['id'] for t in backlog['tasks']}
    ledger39 = read_json(V2 / 'swarm_backlog_20261021/gt25_stop_dependency_closure_replacement.json')
    ledger49 = read_json(AUDITS / 'queue-recovery-expanded-49-summary.json')
    refresh = read_json(AUDITS / 'backlog-refresh-20261027.json')
    historical = {j['key']: j['disposition'] for j in ledger39['jobs']}
    historical.update({j['key']: j['disposition'] for j in ledger49['additional_jobs']})
    watchers33 = [w['name'] for w in refresh['watchers']]
    queues19 = [q['name'] for q in ledger39['queues']]

    rows = {}
    folded = defaultdict(list)
    job_dirs = sorted(d for d in V2.iterdir() if d.is_dir() and is_job_dir(d))
    non_job_dirs = sorted(d.name for d in V2.iterdir() if d.is_dir() and not is_job_dir(d))
    for d in job_dirs:
        name = d.name
        if name in FOLD:
            folded[FOLD[name]].append(d)
            continue
        is_queue = (d / 'run_queue.py').exists() or (d / 'queue_status.json').exists()
        outcome, status, pids, receipt = classify(name, d)
        if name in EXECUTED_BY and outcome == 'never_launched':
            det = classify(EXECUTED_BY[name], V2 / EXECUTED_BY[name])
            outcome, status, receipt = det[0], f'executed by {EXECUTED_BY[name]}: {det[1]}', det[3]
        if (d / 'launch_receipt.json').exists():
            lr = read_json(d / 'launch_receipt.json')
            pids = sorted(set(pids + [lr.get('pid') or lr.get('identity', {}).get('pid')]) - {None})
        kind = 'queue' if is_queue else ('watcher_or_detour' if (d / 'status.json').exists() else
                                         'batch' if any((d / f).exists() for f in ('batch_status.json', 'dispatch_status.json', 'batch_summary.json', 'batch_plan.json')) else
                                         'native_or_audit' if any((d / f).exists() for f in ('native_status.json', 'audit_status.json')) else
                                         'definition' if any(re.search(r'plan|proposal|launch|handoff', p.name) or (p.suffix == '.py' and not SKIP_PY.match(p.name))
                                                             for p in d.iterdir() if p.is_file()) else 'result_or_review')
        rows[name] = {'id': name, 'kind': kind, 'outcome': outcome, 'status': status, 'pids': pids,
                      'terminal_receipt': receipt, 'files_sha256': control_files(d)}
        if is_queue:
            qs = read_json(d / 'queue_status.json') or {}
            plan = read_json(d / 'plan.json') if (d / 'plan.json').exists() else None
            ran = {j['name']: j for j in qs.get('jobs', [])}
            jobs = [j['name'] for j in plan['jobs']] if plan else [j['name'] for j in qs.get('jobs', [])]
            for i, job in enumerate(jobs):
                key = f'{name}/{i}:{job}'
                r = ran.get(job)
                if r is not None:
                    jstatus = r.get('status')
                    if r.get('exit_code') == 0 and jstatus in (None, 'complete_partial_scope') and r.get('summary_exists', True):
                        joutcome = 'completed'
                    elif r.get('exit_code') == 0:
                        joutcome = 'stopped'
                    else:
                        joutcome = 'failed' if r.get('exit_code') not in (None, 0) and jstatus != 'stopped_by_request' else 'stopped'
                    jtext = f"exit {r.get('exit_code')}, {jstatus}"
                    out_dir = Path(r['output'])
                    planned = {j['name']: j for j in plan['jobs']}.get(job, {}) if plan else {}
                    if planned.get('summary'):
                        summary = out_dir / planned['summary']
                    else:  # fixed_data_queue run_queue.py rule
                        summary = out_dir / ('conversion_summary.json' if job == 'um21_tread' else 'batch_summary.json')
                    jreceipt = rel(summary) if summary.exists() else None
                    jfiles = {jreceipt: sha(summary)} if jreceipt else {}
                    if r.get('summary_sha256') and jreceipt and jfiles[jreceipt] != r['summary_sha256']:
                        joutcome, jtext = 'stopped', jtext + '; receipt changed since the queue recorded it'
                elif qs.get('active_job') == job and qs.get('status') == 'running':
                    joutcome, jtext, jreceipt, jfiles = 'stale_running', 'recorded as active job of a queue that is no longer running', None, {}
                else:
                    joutcome, jtext, jreceipt, jfiles = 'never_launched', f"queue {qs.get('status')} before this job", None, {}
                rows[key] = {'id': key, 'kind': 'queue_job', 'outcome': joutcome, 'status': jtext, 'pids': [],
                             'terminal_receipt': jreceipt, 'files_sha256': jfiles, 'queue': name,
                             'queue_recorded_receipt_sha256': (r or {}).get('summary_sha256')}
        if is_queue:  # jobs that appear only in retired plan versions of this queue
            current = set(jobs)
            for old in sorted(p for p in d.iterdir() if p.is_file() and p.name.startswith('plan') and p.name != 'plan.json'):
                retired = read_json(old)
                for j in (retired or {}).get('jobs', []):
                    if j['name'] in current:
                        continue
                    key = f"{name}/retired:{j['name']}"
                    row = rows.setdefault(key, {'id': key, 'kind': 'queue_job', 'outcome': 'never_launched', 'pids': [],
                                                'status': 'listed only in retired plan versions', 'terminal_receipt': None,
                                                'files_sha256': {}, 'queue': name, 'retired_plan_versions': []})
                    row['retired_plan_versions'].append(rel(old))
                    row['files_sha256'][rel(old)] = sha(old)
    # Folded execution records.
    for key, dirs in folded.items():
        row = rows[key]
        for d in dirs:
            outcome, status, pids, receipt = classify(d.name, d)
            row['files_sha256'].update(control_files(d))
            row['pids'] = sorted(set(row['pids'] + pids))
            row.setdefault('execution_records', []).append({'dir': rel(d), 'outcome': outcome, 'status': status})
            if outcome == 'failed' or row['outcome'] in ('never_launched', 'stale_running'):
                row['outcome'], row['status'], row['terminal_receipt'] = outcome, f'{d.name}: {status}', receipt
    # GT21 producer/auditor are distinct jobs (PM-01): keep the auditor as its own row.
    audit = V2 / 'gt21_memory_wait_20261021/attempt_1792594489842444408/source_audit/audit_status.json'
    a = read_json(audit)
    aid = 'gt21_memory_wait_20261021/attempt_1792594489842444408/source_audit'
    rows[aid] = {'id': aid, 'kind': 'batch', 'outcome': 'completed', 'pids': [a['pid']],
                 'status': f"{a['status']} {a['checked_recordings']}/{a['planned_recordings']}",
                 'terminal_receipt': rel(audit), 'files_sha256': {rel(audit): sha(audit)}}

    # Dispositions.
    head_of = {}
    for members in GROUPS.values():
        for m in members[:-1]:
            head_of[m] = members[-1]
    grouped = {m for members in GROUPS.values() for m in members}
    versions = defaultdict(list)  # generic _vN lineages: every older version is replaced by the newest
    for rid, row in rows.items():
        if row['kind'] not in ('queue', 'queue_job') and '/' not in rid and rid not in grouped:
            m = re.match(r'^(.*?)(?:_v(\d+))?(_20261\d{3})$', rid)
            if m:
                versions[m.group(1) + m.group(3)].append((int(m.group(2) or 1), rid))
    version_head = {}
    for members in versions.values():
        if len(members) > 1:
            members.sort()
            for _, rid in members[:-1]:
                version_head[rid] = members[-1][1]
    for rid, row in rows.items():
        base = rid.split('/')[-1].split(':')[-1] if row['kind'] == 'queue_job' else rid
        owner = owner_of(base)
        successor, note = None, NOTES.get(rid, '')
        if row['kind'] == 'queue':
            disp, owner = 'obsolete', 'PM-02'
            note = 'Serial queue orchestration is retired; each of its jobs has its own row. Any new run goes through the reviewed guarded launcher, one job at a time.'
        elif rid in OVERRIDES:
            disp, successor, o, n = OVERRIDES[rid]
            owner, note = o or owner, n or note
        elif rid in version_head:
            disp, successor = 'superseded', version_head[rid]
            note = note or 'An older version; the newest version of the same job replaces it.'
        elif row['outcome'] == 'completed':
            disp = 'completed_unreviewed'
        elif rid in head_of:
            disp, successor = 'superseded', head_of[rid]
        else:
            disp = 'needs_fresh_reviewed_plan'
            if row['outcome'] == 'no_terminal_record':
                note = note or 'No status or terminal receipt; not evidence of success. Redo under a reviewed plan if the owner still needs it.'
        if disp == 'completed_unreviewed' and not note and re.search(r'partial|subset', str(row.get('status'))):
            note = f"Limited scope ({row['status']}); does not cover the dataset's full scope."
        if disp == 'superseded' and successor in rows and owner is None:
            owner = rows[successor].get('owner_task')
        row.update(disposition=disp, successor=successor, owner_task=owner, note=note,
                   dataset=dataset_of(base, row['kind']), historical_disposition=historical.get(rid))
    # Owners of superseded rows follow their chain when no rule applied.
    for row in rows.values():
        if row['owner_task'] is None and row['successor']:
            nxt = row['successor']
            while rows[nxt]['owner_task'] is None and rows[nxt]['successor']:
                nxt = rows[nxt]['successor']
            row['owner_task'] = rows[nxt]['owner_task']
        if row['dataset'] == 'Orchestration' and row['kind'] == 'queue_job':
            row['dataset'] = dataset_of(row['queue'], 'queue_job')
    return rows, dict(task_ids=task_ids, historical=historical, watchers33=watchers33, queues19=queues19,
                      non_job_dirs=non_job_dirs, refresh=refresh, ledger39=ledger39, ledger49=ledger49,
                      version_lineages=sum(1 for v in versions.values() if len(v) > 1))


def terminal(rows, rid, seen=()):
    if rid in seen:
        raise ValueError(f'Supersession cycle at {rid}')
    row = rows[rid]
    return terminal(rows, row['successor'], seen + (rid,)) if row['disposition'] == 'superseded' else rid


def checks(rows, ctx):
    result = {}
    bad = [r['id'] for r in rows.values() if r['disposition'] not in DISPOSITIONS or r['owner_task'] not in ctx['task_ids']]
    result['every_row_has_disposition_and_existing_owner'] = {'pass': not bad, 'violations': bad}
    bad = [r['id'] for r in rows.values() if r['outcome'] in NOT_SUCCESS and r['disposition'] == 'completed_unreviewed']
    result['no_stopped_failed_or_unlaunched_job_counted_complete'] = {'pass': not bad, 'violations': bad}
    bad = [r['id'] for r in rows.values() if r['disposition'] == 'completed_unreviewed' and not (r['terminal_receipt'] and any(len(v) == 64 for v in r['files_sha256'].values()))]
    result['completed_rows_bind_a_hashed_terminal_receipt'] = {'pass': not bad, 'violations': bad}
    bad, ends = [], Counter()
    for r in rows.values():
        if r['disposition'] == 'superseded':
            if r['successor'] not in rows:
                bad.append(r['id'])
                continue
            end = terminal(rows, r['id'])
            ends[rows[end]['disposition']] += 1
    result['supersession_chains_resolve'] = {'pass': not bad, 'violations': bad, 'chain_end_dispositions': dict(ends)}
    missing = sorted(set(ctx['historical']) - set(rows))
    result['all_49_snapshot_jobs_present'] = {'pass': not missing and len(ctx['historical']) == 49, 'missing': missing,
                                              'snapshot_jobs': len(ctx['historical'])}
    missing = sorted(set(ctx['watchers33'] + ctx['queues19']) - set(rows))
    result['all_33_watchers_and_19_queues_present'] = {'pass': not missing, 'missing': missing}
    # Completeness against an independent enumeration of the directory tree and of every queue plan file.
    listed = sorted(e.name for e in os.scandir(V2) if e.is_dir(follow_symlinks=False))
    top = {rid.split('/')[0] for rid in rows if rows[rid]['kind'] != 'queue_job'}
    unaccounted = [n for n in listed if n not in top and not (n in FOLD and FOLD[n] in rows)]
    plan_jobs, missing_jobs = 0, []
    for q in listed:
        qd = V2 / q
        if not ((qd / 'run_queue.py').exists() or (qd / 'queue_status.json').exists()):
            continue
        names = set()
        for f in sorted(qd.iterdir()):
            if f.is_file() and f.name.startswith('plan'):
                for i, j in enumerate((read_json(f) or {}).get('jobs', [])):
                    plan_jobs += 1
                    ok = f'{q}/{i}:{j["name"]}' in rows if f.name == 'plan.json' else (f'{q}/retired:{j["name"]}' in rows or any(r.startswith(f'{q}/') and r.endswith(':' + j['name']) for r in rows))
                    if not ok:
                        missing_jobs.append(f'{q}:{f.name}:{j["name"]}')
        if not (qd / 'plan.json').exists():
            for j in (read_json(qd / 'queue_status.json') or {}).get('jobs', []):
                plan_jobs += 1
                if not any(r.startswith(f'{q}/') and r.endswith(':' + j['name']) for r in rows):
                    missing_jobs.append(f'{q}:queue_status:{j["name"]}')
    result['every_retained_directory_and_plan_job_accounted'] = {
        'pass': not unaccounted and not missing_jobs, 'directories_listed': len(listed), 'directories_as_rows': len(top & set(listed)),
        'directories_folded': sum(1 for n in listed if n in FOLD), 'unaccounted_directories': unaccounted,
        'plan_job_entries_checked': plan_jobs, 'unaccounted_plan_jobs': missing_jobs,
        'top_level_files_not_jobs': sorted(e.name for e in os.scandir(V2) if e.is_file())}
    sp = rows['gt25' + Q + '1:strokepig_native']
    end = rows[terminal(rows, sp['id'])]
    result['strokepig_restored_as_independent_job'] = {
        'pass': end['owner_task'] == 'SP50-F01' and end['disposition'] == 'needs_fresh_reviewed_plan',
        'chain_end': end['id'], 'owner': end['owner_task']}
    return result


def mblue_recheck():
    status = read_json(V2 / 'mblue_priority_handoff_20261021/status.json')
    out = []
    for job in status['jobs']:
        path = Path(job['summary'])
        now = sha(path) if path.exists() else None
        out.append({'job': job['name'], 'summary': rel(path), 'recorded_sha256': job['summary_sha256'],
                    'current_sha256': now, 'match': now == job['summary_sha256'], 'status': job['status']})
    return {'jobs': out, 'all_match': all(j['match'] for j in out),
            'historical_controller_release': {'native_controller_pid': status['native_controller_pid'],
                                              'native_controller_resumed': status['native_controller_resumed'],
                                              'meaning': 'Historical fact retained: the detour released the GT21 controller on 21 Oct. That controller is gone; nothing is resumed now.'}}


def extra_rechecks():
    pairs = {
        'converted_datasets/reconversion_v2/mblue_planar_preserved_early_full_20261021/planar_preservation_summary.json':
            'e8a0d0654bfba2df680080177d6acb2ff950be5f655eee4922483d141ca125a2',
        'converted_datasets/reconversion_v2/mblue_final_acceptance_20261021/scope_evidence.json':
            '5c3c29eadf8afb1ad065a8ae34723baa693fa510716fc0fe4ec2a1902f26bce5',
        'converted_datasets/reconversion_v2/um21_running_full_20261020/source_comparison.json':
            '9fb0376303eec610573120f215c45df28ca5818737500da3978c2f0e4c65d21b',
        'converted_datasets/reconversion_v2/um21_tread_corrected_20261020/conversion_summary.json':
            '349b896e7daa28589d1af705a7be6fbbb1af32f7b09f092d289e63869554172d',
        'converted_datasets/reconversion_v2/gt21_force_corrected_full_20261021/batch_status.json':
            'c07323aa54db90cd3d1af6c522a483453e2fc0e90dd30e5b6b4369ddc1ff27c3',
        'converted_datasets/reconversion_v2/gt21_memory_wait_20261021/attempt_1792594489842444408/source_audit/audit_status.json':
            'd524fe57e06d666e93106c1e4e65039b5d693c62b634291df968bc3b728eec9c',
    }
    return [{'path': p, 'recorded_sha256': s, 'current_sha256': sha(ROOT / p), 'match': sha(ROOT / p) == s} for p, s in pairs.items()]


def census(rows):
    boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    pids = sorted({p for r in rows.values() for p in r['pids']} | {402224, 402226, 516926, 516927})
    present = {}
    for pid in pids:
        cmd = proc_identity(pid)
        if cmd is not None:
            present[pid] = cmd
    owned = [pid for pid, cmd in present.items() if re.search(r'reconversion_v2|contributor_tools|MATLAB|opensim', cmd)]
    return {'linux': {'checked_at_utc': datetime.now(timezone.utc).isoformat(timespec='seconds'), 'boot_id': boot,
                      'historical_boot_id_per_pm01': '8b0e06c4 (2026-10-18 to 2026-10-21)',
                      'historical_pids_checked': len(pids), 'pids_present_now': present,
                      'pids_present_with_job_command_line': owned,
                      'note': 'Every recorded PID belongs to the previous boot. A PID number present now is an unrelated reuse unless its command line names a job.'},
            'windows': windows_census()}


# ---------------------------------------------------------------- figures and sheet
INK, MUTED, GRID, BAD = '#20252B', '#5b6672', '#dde2e7', '#c0392b'
DCOLOR = {'completed_unreviewed': '#2a78d6', 'superseded': '#9aa6b2', 'needs_fresh_reviewed_plan': '#eda100',
          'quarantined_known_bad': '#c0392b', 'obsolete': '#5b6672', 'unlisted': BAD}
DLABEL = {'completed_unreviewed': 'done, unreviewed', 'superseded': 'replaced', 'needs_fresh_reviewed_plan': 'new plan needed',
          'quarantined_known_bad': 'known bad', 'obsolete': 'closed', 'unlisted': 'NO STATUS'}
OLABEL = {'completed': 'completed', 'failed': 'failed', 'stopped': 'stopped', 'stale_running': 'says running,\nbut gone',
          'never_launched': 'never ran', 'no_terminal_record': 'no record\nof result'}
SHORT = {'UMich 2021': 'UMich 2021', 'GaTech 2021': 'GaTech 2021', 'GaTech 2023': 'GaTech 2023', 'GaTech 2024': 'GaTech 2024',
         'GaTech 2025': 'GaTech 2025', 'MBLUE': 'MBLUE', 'Gait120': 'Gait120', 'StrokePiG': 'StrokePiG', 'Fukuchi 2018': 'Fukuchi',
         'UMich 2024 knee exo': 'UMich knee exo', 'AddBiomechanics': 'AddBiomech.', 'Orchestration': 'Queues, ops'}


def style():
    plt.rcParams.update({'font.size': 17, 'axes.edgecolor': GRID, 'axes.labelcolor': INK, 'xtick.color': INK,
                         'ytick.color': INK, 'text.color': INK, 'font.family': 'DejaVu Sans'})


def matrix(ax, counts, row_labels, col_keys, forbidden=()):
    peak = max([1] + list(counts.values()))
    for i, r in enumerate(row_labels):
        for j, c in enumerate(col_keys):
            n = counts.get((r, c), 0)
            bad = (r, c) in forbidden
            alpha = min(1, .25 + .75 * (n / peak) ** .5) if n else 1
            face = DCOLOR[c] if n else '#ffffff'
            ax.add_patch(plt.Rectangle((j, i), 1, 1, facecolor=face, alpha=alpha, edgecolor=BAD if bad else GRID,
                                       lw=2.4 if bad else 1, ls='--' if bad and not n else '-'))
            if n:
                rgb = [alpha * x + (1 - alpha) for x in matplotlib.colors.to_rgb(face)]
                light = .2126 * rgb[0] + .7152 * rgb[1] + .0722 * rgb[2] > .55
                ax.text(j + .5, i + .5, str(n), ha='center', va='center', fontsize=18, fontweight='bold',
                        color=INK if light else 'white')
            elif bad:
                ax.text(j + .5, i + .5, '0', ha='center', va='center', fontsize=17, color=BAD)
    ax.set_xlim(0, len(col_keys)); ax.set_ylim(len(row_labels), 0)
    ax.set_xticks([j + .5 for j in range(len(col_keys))], [DLABEL[c] for c in col_keys], fontsize=17,
                  rotation=40, ha='left', rotation_mode='anchor')
    for lab, c in zip(ax.get_xticklabels(), col_keys):
        if c == 'unlisted':
            lab.set_color(BAD)
    ax.set_yticks([i + .5 for i in range(len(row_labels))], row_labels, fontsize=17)
    ax.tick_params(length=0); ax.xaxis.tick_top()
    for sp in ax.spines.values():
        sp.set_visible(False)


def figures(rows, result):
    style()
    SHEET.mkdir(parents=True, exist_ok=True)
    order = list(SHORT)
    totals = Counter(r['dataset'] for r in rows.values())
    labels = {d: f'{SHORT[d]} ({totals[d]})' for d in order if totals[d]}
    counts = Counter((labels[r['dataset']], r['disposition']) for r in rows.values())
    # Unaccounted directories have no row and therefore no dataset: they land in the no-status column by name.
    for name in result['every_retained_directory_and_plan_job_accounted']['unaccounted_directories']:
        counts[(labels.get(dataset_of(name, 'result_or_review'), labels['Orchestration']), 'unlisted')] += 1
    cols = DISPOSITIONS + ['unlisted']
    rlabels = list(labels.values())
    fig, ax = plt.subplots(figsize=(6.0, .6 * len(rlabels) + 1.6))
    matrix(ax, counts, rlabels, cols, forbidden={(r, 'unlisted') for r in rlabels})
    fig.savefig(SHEET / 'fig1_dispositions.png', dpi=130, bbox_inches='tight'); plt.close(fig)

    outcomes = ['completed', 'failed', 'stopped', 'stale_running', 'never_launched', 'no_terminal_record']
    counts = Counter((OLABEL[r['outcome']], r['disposition']) for r in rows.values())
    forbidden = {(OLABEL[o], 'completed_unreviewed') for o in outcomes if o != 'completed'}
    fig, ax = plt.subplots(figsize=(6.0, .75 * len(outcomes) + 1.6))
    matrix(ax, counts, [OLABEL[o] for o in outcomes], DISPOSITIONS, forbidden)
    fig.savefig(SHEET / 'fig2_outcomes.png', dpi=130, bbox_inches='tight'); plt.close(fig)


def sheet(rows, result, mb, extra, cen):
    n = len(rows)
    disp = Counter(r['disposition'] for r in rows.values())
    win = cen['windows']
    alive = cen['linux']['pids_present_with_job_command_line'] or (win.get('matlab_python_opensim_workers') if win.get('checked') else None)
    comp = result['every_retained_directory_and_plan_job_accounted']
    missing = len(comp['unaccounted_directories']) + len(comp['unaccounted_plan_jobs'])
    chips = [('pass' if comp['pass'] else 'fail',
              f"all {comp['directories_listed']} old job folders and every queued job listed" if comp['pass'] else f'{missing} old jobs not listed'),
             ('pass' if result['every_row_has_disposition_and_existing_owner']['pass'] else 'fail', f'{n} jobs, each with one status and owner task'),
             ('pass' if result['no_stopped_failed_or_unlaunched_job_counted_complete']['pass'] else 'fail', 'no stopped or failed job counted as done'),
             ('pass' if not alive and win.get('checked') else ('unchecked' if not win.get('checked') else 'fail'), 'no old job process alive (Linux, Windows)'),
             ('pass' if mb['all_match'] else 'fail', 'four MBLUE detour results unchanged'),
             ('pass' if result['strokepig_restored_as_independent_job']['pass'] else 'fail', 'StrokePiG job kept, independent of GT25'),
             ('unchecked', 'GT25 streaming pilot: ankle-sign effect'),
             ('unchecked', 'scientific content of done results')]
    page(SHEET / 'index.html', title='Old job statuses',
         ask='Look at 2 figures. Reply ok, or say what looks wrong.',
         headline=f'Every old job has one current status; none restarts as is ({n} jobs)',
         chips=chips,
         figures=[('fig1_dispositions.png', 'Does every old job have a current status?',
                   'Dashed red column: jobs left without one. Replaced work continues in its successor; closed work ends.',
                   'Count matrix of datasets by current status, with a column for jobs without a status'),
                  ('fig2_outcomes.png', 'Is any stopped or failed job counted as done?',
                   'Dashed red cells must stay zero.',
                   'Count matrix of what happened by current status, with forbidden cells outlined')],
         not_shown=['Whether done results are scientifically right',
                    'Which job runs first (each task decides)'],
         reply='ok  |  what looks wrong',
         details=[f"Counts: {', '.join(f'{k} {v}' for k, v in sorted(disp.items()))}.",
                  'A job here is every top-level folder of the old reconversion area (each was written by a plan, launcher, pilot, audit or review) plus every job in current and retired queue plans.',
                  'Evidence: docs/quality/audits/pm02-job-dispositions.json',
                  'Builder: contributor_tools/review_pm02_dispositions.py'])


def main():
    rows, ctx = build()
    result = checks(rows, ctx)
    mb = mblue_recheck()
    extra = extra_rechecks()
    cen = census(rows)
    figures(rows, result)
    sheet(rows, result, mb, extra, cen)
    git = subprocess.run(['git', 'rev-parse', 'HEAD'], capture_output=True, text=True, cwd=ROOT).stdout.strip()
    by_disp = Counter(r['disposition'] for r in rows.values())
    by_owner = defaultdict(Counter)
    for r in rows.values():
        by_owner[r['owner_task']][r['disposition']] += 1
    report = {
        'task_id': 'PM-02',
        'checked_at_utc': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'status': 'every_retained_job_dispositioned_no_job_started',
        'scientific_approval': False,
        'method': 'Read-only. Bounded JSON receipt reads (4 MiB cap), SHA256 of small control files, /proc PID check and a Win32_Process census. No arrays loaded, no process started or signalled, no file under converted_datasets/ modified.',
        'repository_head': git,
        'builder': {'path': 'contributor_tools/review_pm02_dispositions.py', 'sha256': sha(Path(__file__))},
        'inputs_sha256': {p: sha(ROOT / p) for p in INPUTS},
        'scope': {
            'definition': 'Every top-level directory of converted_datasets/reconversion_v2 is a retained job record, because each was written by a plan, launcher, pilot, audit, review or staging step. Each gets a row unless it is the execution record of a queue job (folded into that row). Every job in a current or retired queue plan, or in a plan-less queue status, also gets a row. Completeness is checked against an independent directory and plan-file enumeration.',
            'rows': len(rows),
            'job_directories': sum(1 for r in rows.values() if r['kind'] != 'queue_job') - 1,
            'queue_jobs': sum(1 for r in rows.values() if r['kind'] == 'queue_job'),
            'separate_gt21_auditor_row': 1,
            'directories_folded_into_queue_jobs': sorted(FOLD),
            'kinds': dict(Counter(r['kind'] for r in rows.values())),
            'version_lineages': ctx['version_lineages'],
            'beyond_snapshots': 'Includes the 20 Oct generation (four fixed-data queues, the corrected queue and three dispatchers), all detours, native MATLAB pilots, subset auditors, readbacks, reviews, proposals, prepared plans and drafts absent from the 39/49 snapshots, and jobs listed only in retired queue plan versions.',
            'revision': '2026-10-27 r2: widened after independent verification (docs/maintainers/handoffs/PM-02-verify.json) found about 35 directories with status or plan records that had no row.',
        },
        'disposition_definitions': {
            'completed_unreviewed': 'Terminal success receipt, rehashed now. Evidence for the owner task only; not scientific approval.',
            'superseded': 'A named later job or result replaces it; the chain ends in another disposition.',
            'needs_fresh_reviewed_plan': 'Still in scope. The owner task writes a new reviewed plan for the guarded single-job launcher; the old definition is never resumed.',
            'quarantined_known_bad': 'Recipe known to be wrong; never rerun as defined. The owner task must settle the correction first.',
            'obsolete': 'No longer needed or no longer reproducible; closed by PM-02.'},
        'counts': {'by_disposition': dict(by_disp), 'by_outcome': dict(Counter(r['outcome'] for r in rows.values())),
                   'by_dataset': dict(Counter(r['dataset'] for r in rows.values())),
                   'by_owner_task': {k: dict(v) for k, v in sorted(by_owner.items(), key=lambda kv: str(kv[0]))}},
        'checks': result,
        'mblue_detour_recheck': mb,
        'receipt_rechecks': extra,
        'host_census': cen,
        'needs_fresh_plan_by_owner': {k: sorted(r['id'] for r in rows.values() if r['owner_task'] == k and r['disposition'] == 'needs_fresh_reviewed_plan')
                                      for k in sorted({r["owner_task"] for r in rows.values() if r["disposition"] == "needs_fresh_reviewed_plan"}, key=str)},
        'unresolved': [
            'gt25_streaming_transfer_pilot_v2 (28 observations) predates the GT25 ankle-sign stop and its independent source audit never ran; GT25-P01 must decide whether the sign error applies before using it.',
            'gt21_metadata_corrected_20261021 failed at AB06 treadmill_07_01; its cause was not investigated because the force-corrected batch replaced it.',
            'Owner mappings follow directory names, queue plans and watcher references; the owner task re-reads its rows before writing a plan.',
        ],
        'limitations': [
            'Receipts and hashes only; no scientific output was reread. completed_unreviewed is not approval.',
            'Process absence is a point-in-time check; any launch must repeat it.',
            'Plans larger than 4 MiB are recorded by size, not hashed.',
        ],
        'rows': [rows[k] for k in sorted(rows)],
    }
    OUT.write_text(json.dumps(report, indent=1, default=str) + '\n')
    print(json.dumps({'rows': len(rows), 'by_disposition': dict(by_disp), 'checks': {k: v['pass'] for k, v in result.items()},
                      'mblue_all_match': mb['all_match'], 'extra_match': all(e['match'] for e in extra),
                      'linux_alive': cen['linux']['pids_present_with_job_command_line'],
                      'windows_workers': cen['windows'].get('matlab_python_opensim_workers')}, indent=1))


if __name__ == '__main__':
    main()
