"""Tests for main module."""

from f8a_report.main import time_to_generate_monthly_report, main
from unittest import mock


class TodayMockClass:
    """Mock class for `today` from datetime module."""

    def __init__(self, day):
        """Construct the class and initialize day attribute."""
        self.day = day


def test_time_to_generate_monthly_report():
    """Test the function time_to_generate_monthly_report."""
    today = TodayMockClass(1)
    assert time_to_generate_monthly_report(today) is True

    today = TodayMockClass(30)
    assert time_to_generate_monthly_report(today) is False


@mock.patch('f8a_report.main.ReportHelper.get_report', return_value=[{}, True])
@mock.patch('f8a_report.main.ReportHelper.retrain', return_value=True)
def test_main(_mock1, _mock2):
    """Test the function main."""
    resp = main()
    assert (isinstance(resp, dict))
