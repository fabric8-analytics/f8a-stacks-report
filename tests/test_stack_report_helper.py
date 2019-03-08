"""Tests for classes from stack_report_helper module."""

from f8a_report.report_helper import ReportHelper, S3Helper, Postgres
from pathlib import Path
import pytest
from unittest import mock
import json

r = ReportHelper()
s = S3Helper()

with open('tests/data/collateddata.json', 'r') as f:
    collateddata = json.load(f)

with open('tests/data/stackdata.json', 'r') as f:
    stackdata = f.read()

with open('tests/data/ingestiondata.json', 'r') as f:
    ingestiondata = f.read()
    ingestiondata = json.loads(ingestiondata)


def test_validate_and_process_date_success():
    """Test the success scenario of the function validate_and_process_date."""
    res = r.validate_and_process_date('2019-01-01')
    assert res == '2019-01-01'

    res = r.validate_and_process_date('1900-01-01')
    assert res == '1900-01-01'


def test_validate_and_process_date_no_real_dates():
    """Test the failure scenario of the function validate_and_process_date."""
    with pytest.raises(ValueError) as e:
        r.validate_and_process_date('2019-01-32')
        assert str(e.value) == 'Incorrect data format, should be YYYY-MM-DD'

    with pytest.raises(ValueError) as e:
        r.validate_and_process_date('0000-01-01')
        assert str(e.value) == 'Incorrect data format, should be YYYY-MM-DD'


def test_validate_and_process_date_failure():
    """Test the failure scenario of the function validate_and_process_date."""
    with pytest.raises(ValueError) as e:
        r.validate_and_process_date('xyzabc')
        assert str(e.value) == 'Incorrect data format, should be YYYY-MM-DD'

    with pytest.raises(ValueError) as e:
        r.validate_and_process_date('')
        assert str(e.value) == 'Incorrect data format, should be YYYY-MM-DD'


def test_retrieve_stack_analyses_ids_wrong_dates():
    """Test the failure scenario of the function retrieve_stack_analyses_ids."""
    # both dates are incorrect
    with pytest.raises(ValueError) as e:
        r.retrieve_stack_analyses_ids('xyzabc', 'foobar')
        assert str(e.value) == 'Invalid date format'

    # start_date is incorrect
    with pytest.raises(ValueError) as e:
        r.retrieve_stack_analyses_ids('foobar', '2019-01-01')
        assert str(e.value) == 'Invalid date format'

    # start_date is incorrect
    with pytest.raises(ValueError) as e:
        r.retrieve_stack_analyses_ids('0000-01-01', '2019-01-01')
        assert str(e.value) == 'Invalid date format'

    # start_date is incorrect
    with pytest.raises(ValueError) as e:
        r.retrieve_stack_analyses_ids('2019-01-32', '2019-01-01')
        assert str(e.value) == 'Invalid date format'

    # end_date is incorrect
    with pytest.raises(ValueError) as e:
        r.retrieve_stack_analyses_ids('2019-01-01', 'foobar')
        assert str(e.value) == 'Invalid date format'

    # end_date is incorrect
    with pytest.raises(ValueError) as e:
        r.retrieve_stack_analyses_ids('2019-01-01', '2019-01-32')
        assert str(e.value) == 'Invalid date format'


def test_flatten_list_empty_input():
    """Test the success scenario of the function flatten_list."""
    assert r.flatten_list([]) == []
    assert r.flatten_list([[]]) == []


def test_flatten_list():
    """Test the success scenario of the function flatten_list."""
    assert r.flatten_list([[1]]) == [1]
    assert r.flatten_list([[1, 2]]) == [1, 2]
    assert r.flatten_list([[1, 2], [3, 4]]) == [1, 2, 3, 4]


def test_flatten_list_already_flat_list():
    """Test the success scenario of the function flatten_list."""
    with pytest.raises(TypeError) as e:
        r.flatten_list([1])
        assert e.value == "TypeError: 'int' object is not iterable"

    with pytest.raises(TypeError) as e:
        r.flatten_list([1, 2]) == [1, 2]
        assert e.value == "TypeError: 'int' object is not iterable"

    with pytest.raises(TypeError) as e:
        r.flatten_list([1, 2, 3, 4]) == [1, 2, 3, 4]
        assert e.value == "TypeError: 'int' object is not iterable"


def test_datediff_in_millisecs_same_dates():
    """Test the success scenario of the function datediff_in_millisecs."""
    start, end = '2018-08-23T17:05:52.912429', '2018-08-23T17:05:52.912429'
    assert r.datediff_in_millisecs(start, end) == 0


def test_datediff_in_millisecs():
    """Test the success scenario of the function datediff_in_millisecs."""
    start, end = '2018-08-23T17:05:52.0', '2018-08-23T17:05:53.1'
    # the difference is always zero or positive
    assert r.datediff_in_millisecs(start, end) == 100.0

    start, end = '2018-08-23T17:05:52.912429', '2018-08-23T17:05:53.624783'
    # the difference is always zero or positive
    assert r.datediff_in_millisecs(start, end) == 712.354


def test_datediff_in_millisecs_no_negative_result():
    """Test the success scenario of the function datediff_in_millisecs."""
    start, end = '2018-08-23T17:05:53.624783', '2018-08-23T17:05:52.912429'
    # the difference is always zero or positive
    assert r.datediff_in_millisecs(start, end) == 287.646


def test_datediff_in_millisecs_one_sec_change():
    """Test the success scenario of the function datediff_in_millisecs."""
    start, end = '2018-08-23T17:05:52.0', '2018-08-24T17:05:53.0'
    assert r.datediff_in_millisecs(start, end) == 0
    assert r.datediff_in_millisecs(end, start) == 0


def test_datediff_in_millisecs_one_day_change():
    """Test the success scenario of the function datediff_in_millisecs."""
    start, end = '2018-08-23T17:05:53.624783', '2018-08-24T17:05:53.624783'
    assert r.datediff_in_millisecs(start, end) == 0
    assert r.datediff_in_millisecs(end, start) == 0


def test_normalize_deps_list():
    """Test the success scenario of the function normalize_deps_list."""
    deps_list = [{'package': 'abc', 'version': '1.0.0'}]
    assert r.normalize_deps_list(deps_list) == ['abc 1.0.0']


def test_normalize_deps_list_empty_input():
    """Test the success scenario of the function normalize_deps_list."""
    deps_list = []
    assert r.normalize_deps_list(deps_list) == []


def test_normalize_deps_list_sorted():
    """Test the success scenario of the function normalize_deps_list."""
    deps_list = [{'package': 'abc', 'version': '1.0.0'},
                 {'package': 'zzz', 'version': '2.0.0'}]
    assert r.normalize_deps_list(deps_list) == ['abc 1.0.0', 'zzz 2.0.0']

    deps_list = [{'package': 'zzz', 'version': '1.0.0'},
                 {'package': 'abc', 'version': '2.0.0'}]
    assert r.normalize_deps_list(deps_list) == ['abc 2.0.0', 'zzz 1.0.0']


def test_populate_key_count_success():
    """Test the success scenario of the function populate_key_count."""
    assert (r.populate_key_count(['abc 1.0.0', 'xyz 1.0.0', 'abc 1.0.0']) ==
            {'abc 1.0.0': 2, 'xyz 1.0.0': 1})


def test_populate_key_count_failure():
    """Test the failure scenario of the function populate_key_count."""
    with pytest.raises(Exception) as e:
        r.populate_key_count([[], {}])
        assert e.value == 'TypeError("unhashable type: \'list\'",)'


def test_s3helper():
    """Test the failure scenario of the __init__ method of the class S3Helper."""
    assert s.s3 is not None


@mock.patch('f8a_report.report_helper.S3Helper.store_json_content', return_value=True)
def test_store_training_data(_mock1):
    """Test the success scenario for storing Retraining Data in their respective buckets."""
    resp = r.store_training_data(collateddata)

    assert resp is None


@mock.patch('f8a_report.report_helper.S3Helper.store_json_content', return_value=True)
@mock.patch('f8a_report.report_helper.S3Helper.read_json_object', return_value=collateddata)
def test_collate_raw_data(_mock1, _mock2):
    """Test result collation success scenario."""
    result = r.collate_raw_data(collateddata, 'weekly')

    assert result is not None


@mock.patch('f8a_report.report_helper.S3Helper.store_json_content', return_value=True)
@mock.patch('f8a_report.report_helper.ReportHelper.collate_raw_data', return_value=collateddata)
@mock.patch('f8a_report.report_helper.ReportHelper.store_training_data', return_value=True)
def test_normalize_worker_data(_mock1, _mock2, _mock3):
    """Test the success scenario of the function normalize_worker_data."""
    resp = r.normalize_worker_data('2018-10-10', '2018-10-18',
                                   stackdata, 'stack_aggregator_v2', 'weekly')

    assert resp is not None


@mock.patch('f8a_report.report_helper.S3Helper.store_json_content', return_value=True)
def test_normalize_worker_data_no_stack_aggregator(_mock_count):
    """Test the success scenario of the function normalize_worker_data."""
    resp = r.normalize_worker_data('2018-10-10', '2018-10-18',
                                   stackdata, 'something_different_from_stack_aggregator',
                                   'weekly')

    assert resp is None


@mock.patch('f8a_report.report_helper.ReportHelper.retrieve_worker_results', return_value=True)
@mock.patch('f8a_report.report_helper.ReportHelper.retrieve_stack_analyses_ids', return_value=['1'])
def test_get_report(_mock1, _mock2):
    """Test sucess Get Report."""
    res, ing_res = r.get_report('2018-10-10', '2018-10-18')
    assert res is True


@mock.patch('f8a_report.report_helper.ReportHelper.retrieve_worker_results', return_value=True)
@mock.patch('f8a_report.report_helper.ReportHelper.retrieve_stack_analyses_ids', return_value=[])
def test_get_report(_mock1, _mock2):
    """Test failure Get Report."""
    res, ing_res = r.get_report('2018-10-10', '2018-10-18')
    assert res is False


def test_retrieve_worker_results():
    """Test failure worker results."""
    res = r.retrieve_worker_results('2018-10-10', '2018-10-18', ['1', '2'], [])
    assert res == {}


@mock.patch('f8a_report.report_helper.S3Helper.store_json_content', return_value=True)
def test_normalize_ingestion_data(_mock1):
    """Test the success scenario of the function normalize_worker_data."""
    resp = r.normalize_ingestion_data('2018-10-10', '2018-10-18', ingestiondata, 'daily')
    assert resp is not None


def test_retrieve_ingestion_results():
    """Test failure worker results."""
    res = r.retrieve_ingestion_results('2015-10-10', '2015-10-18')
    assert res == {'EPV_GRAPH_FAILED_DATA': '[]', 'EPV_INGESTION_DATA': '[]'}
