from contributor_tools.run_gt21_with_memory_wait import prelaunch_memory_refusal


def refusal(tmp_path):
    for name in ['options.json','input_manifest.json']:(tmp_path/name).write_text('{}')
    (tmp_path/'launcher.log').write_text('Windows needs the hard limit plus 2 GiB available before launch')


def test_only_proven_prelaunch_refusal_can_retry(tmp_path):
    refusal(tmp_path)
    assert prelaunch_memory_refusal(tmp_path)
    (tmp_path/'native_status.json').write_text('{}')
    assert not prelaunch_memory_refusal(tmp_path)


def test_partial_output_and_other_errors_never_retry(tmp_path):
    refusal(tmp_path)
    (tmp_path/'phase.parquet').write_bytes(b'partial')
    assert not prelaunch_memory_refusal(tmp_path)
    (tmp_path/'phase.parquet').unlink()
    (tmp_path/'launcher.log').write_text('Native worker exceeded memory limit')
    assert not prelaunch_memory_refusal(tmp_path)


def test_native_workspace_means_launch_may_have_started(tmp_path):
    refusal(tmp_path);(tmp_path/'temp').mkdir()
    assert not prelaunch_memory_refusal(tmp_path)
