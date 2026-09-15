from types import SimpleNamespace
from unittest.mock import Mock

import numpy as np
import pytest

from nanomech.nm_io import get_offset_datapoints, load_nhf_file


def load_fake(tmp_path, monkeypatch, segments):
    source = tmp_path / 'sample.nhf'
    source.touch()
    measurement = SimpleNamespace(segment=segments)
    reader = SimpleNamespace(
        measurement={'measurement': measurement},
        measurement_name=lambda index: 'measurement', version=lambda: (2, 1))
    monkeypatch.setattr('nanomech.nm_io.nhf_reader.NHFFileReader', lambda *a, **k: reader)
    return load_nhf_file(source)


def explicit_segment():
    arrays = {'channel_data_offsets': np.array([0, 3]),
              'number_of_datapoints_acquired': np.array([3, 4])}
    return SimpleNamespace(name='Advance', read_channel=Mock(
        side_effect=lambda name: SimpleNamespace(dataset=arrays[name])))


def test_shared_metadata_read_once_and_owned(tmp_path, monkeypatch):
    segment = explicit_segment()
    measurement = load_fake(tmp_path, monkeypatch, {'Advance': segment})
    first = get_offset_datapoints(segment, SimpleNamespace())
    for _ in range(10):
        assert get_offset_datapoints(segment, SimpleNamespace()) is first
    assert segment.read_channel.call_count == 2
    assert measurement._nanomech_offset_cache['Advance']['shared'] is first
    np.testing.assert_array_equal(first[0], [0, 3])
    np.testing.assert_array_equal(first[1], [3, 4])
    segment.read_channel('channel_data_offsets').dataset[0] = 99
    assert first[0][0] == 0
    with pytest.raises(ValueError):
        first[0][0] = 42


def test_blocks_are_cached_per_source_and_failures_retry(tmp_path, monkeypatch):
    segment = SimpleNamespace(
        name='VEA', read_channel=Mock(side_effect=KeyError('missing')),
        find_dataset_by_attribute_value=Mock(side_effect=[
            np.array([3, 4]), ValueError('temporary'), np.array([5, 6])]))
    load_fake(tmp_path, monkeypatch, {'VEA': segment})
    a = SimpleNamespace(attribute={'dataset_block_size_source': 'a'})
    b = SimpleNamespace(attribute={'dataset_block_size_source': 'b'})
    first = get_offset_datapoints(segment, a)
    assert get_offset_datapoints(segment, a) is first
    with pytest.raises(ValueError, match='temporary'):
        get_offset_datapoints(segment, b)
    second = get_offset_datapoints(segment, b)
    assert get_offset_datapoints(segment, b) is second
    np.testing.assert_array_equal(first[0], [0, 3, 7])
    np.testing.assert_array_equal(first[1], [3, 4])
    np.testing.assert_array_equal(second[0], [0, 5, 11])
    np.testing.assert_array_equal(second[1], [5, 6])
    assert segment.read_channel.call_count == 1
    assert segment.find_dataset_by_attribute_value.call_count == 3


def test_measurements_and_segments_are_isolated(tmp_path, monkeypatch):
    a, b, c = explicit_segment(), explicit_segment(), explicit_segment()
    first = load_fake(tmp_path, monkeypatch, {'Advance': a, 'Retract': b})
    second = load_fake(tmp_path, monkeypatch, {'Advance': c})
    results = [get_offset_datapoints(s, SimpleNamespace()) for s in (a, b, c)]
    assert first._nanomech_offset_cache is not second._nanomech_offset_cache
    assert len({id(result) for result in results}) == 3
    assert all(s.read_channel.call_count == 2 for s in (a, b, c))


def test_standalone_segment_remains_supported():
    segment = explicit_segment()
    get_offset_datapoints(segment, SimpleNamespace())
    get_offset_datapoints(segment, SimpleNamespace())
    assert segment.read_channel.call_count == 4
