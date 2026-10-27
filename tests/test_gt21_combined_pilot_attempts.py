"""Existing pilot attempts are evidence, not resumable audit output directories."""
import pytest

from contributor_tools.run_gt21_combined_pilot import require_unused_summary


@pytest.mark.parametrize('content', [
    '{"status":"combined_pilot_source_checked_unreviewed"}',
    '{"status":"failed_incomplete"}', '{"status":"running"}', '', 'partial json',
])
def test_any_existing_summary_is_preserved(tmp_path, content):
    summary = tmp_path / 'pilot_summary.json'
    summary.write_text(content)
    with pytest.raises(FileExistsError, match='use a new root'):
        require_unused_summary(tmp_path)
    assert summary.read_text() == content


def test_unexecuted_prepared_root_allowed(tmp_path):
    (tmp_path / 'pilot_plan.json').write_text('{}')
    require_unused_summary(tmp_path)
    assert not (tmp_path / 'pilot_summary.json').exists()


def test_dangling_summary_link_refused(tmp_path):
    (tmp_path / 'pilot_summary.json').symlink_to(tmp_path / 'missing')
    with pytest.raises(FileExistsError):
        require_unused_summary(tmp_path)
