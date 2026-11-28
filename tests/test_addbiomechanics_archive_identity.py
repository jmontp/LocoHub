"""Do not flatten participants or delete archive evidence during extraction."""
import importlib.util
import json
from pathlib import Path
import zipfile

import pytest

SOURCE = Path(__file__).resolve().parents[1] / 'contributor_tools/conversion_scripts/AddBiomechanics/extract_source_archive.py'
spec = importlib.util.spec_from_file_location('source_archive', SOURCE)
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)


def archive(tmp_path, files):
    path = tmp_path / 'source.zip'
    with zipfile.ZipFile(path, 'w') as stream:
        for name, value in files:
            stream.writestr(name, value)
    return path


def test_duplicate_basenames_retain_distinct_source_paths_and_other_metadata(tmp_path):
    source = archive(tmp_path, [('s1/data.b3d', b'first'), ('s2/data.b3d', b'second'), ('s1/metadata.json', b'{"source":1}')])
    original = source.read_bytes()
    output = tmp_path / 'out'
    inspected = tool.extract(source, output)
    assert inspected['status'] == 'inspected_not_extracted' and not output.exists()
    result = tool.extract(source, output, run=True, reserve_bytes=0)
    assert (output / 'source/s1/data.b3d').read_bytes() == b'first'
    assert (output / 'source/s2/data.b3d').read_bytes() == b'second'
    assert (output / 'source/s1/metadata.json').read_bytes() == b'{"source":1}'
    assert source.read_bytes() == original
    assert len(result['files']) == 3
    assert all(row['sha256'] == tool.digest(output / row['extracted_path']) for row in result['files'])
    with pytest.raises(FileExistsError):
        tool.extract(source, output, run=True, reserve_bytes=0)


@pytest.mark.parametrize('names', [('../escaped.b3d',), ('/absolute.b3d',), ('s\\x.b3d',), ('s/x', 'S/X'), ('s', 's/x')])
def test_unsafe_or_colliding_source_paths_rejected_before_output(tmp_path, names):
    source = archive(tmp_path, [(name, b'bytes') for name in names])
    output = tmp_path / 'out'
    with pytest.raises(ValueError):
        tool.extract(source, output, run=True, reserve_bytes=0)
    assert not output.exists()


def test_interrupted_extraction_preserves_partial_and_source(tmp_path):
    source = archive(tmp_path, [('s/file.b3d', b'bytes')])
    original = source.read_bytes()
    calls = []
    def guard():
        calls.append(1)
        if len(calls) == 4:
            raise MemoryError('synthetic resource guard')
    output = tmp_path / 'out'
    with pytest.raises(MemoryError):
        tool.extract(source, output, run=True, reserve_bytes=0, guard=guard)
    receipt = json.loads((output / 'extraction.json').read_text())
    assert receipt['status'] == 'incomplete_partial_preserved'
    assert source.read_bytes() == original
    assert (output / 'source/s/file.b3d').exists()
