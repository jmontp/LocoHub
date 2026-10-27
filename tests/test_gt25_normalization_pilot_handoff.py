"""Small stdlib acceptance fixtures; no scientific input or child workers."""
import json
import pytest
from contributor_tools.run_gt25_normalization_pilot_v4 import acceptance, digest, verify


def test_exact_transfer_coverage():
    good = dict(status='streaming_transfer_converted_unreviewed', observations=28,
                rows=4200, scientific_approval=False)
    acceptance(good, 'conversion')
    for change in ({'observations': 27}, {'rows': 4199}, {'scientific_approval': True}):
        with pytest.raises(ValueError):
            acceptance({**good, **change}, 'conversion')


def test_audit_must_include_source_aliases():
    good = dict(status='independent_raw_transfer_events_and_values_checked_unreviewed',
                observations_checked=28, rows_checked=4200,
                numeric_features_checked=92, scientific_approval=False)
    acceptance(good, 'audit')
    with pytest.raises(ValueError):
        acceptance({**good, 'numeric_features_checked': 74}, 'audit')


def test_changed_evidence_rejected(tmp_path):
    source = tmp_path / 'source.txt'
    source.write_text('synthetic source')
    binding = {str(source): digest(source)}
    verify(binding)
    source.write_text('different source')
    with pytest.raises(ValueError):
        verify(binding)
