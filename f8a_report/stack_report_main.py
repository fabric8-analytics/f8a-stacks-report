"""Weekly stacks report."""

import logging
from datetime import datetime as dt, timedelta
from report_helper import ReportHelper
from v2.report_generator import StackReportBuilder

logger = logging.getLogger(__file__)


def time_to_generate_monthly_report(today):
    """Check whether it is the right time to generate monthly report."""
    # We will make three attempts to generate the monthly report every month
    return today.day in (1, 2, 3)


def main():
    """Generate the weekly stacks report."""
    r = ReportHelper()
    report_builder_v2 = StackReportBuilder(ReportHelper)
    today = dt.today()
    start_date = (today - timedelta(days=1)).strftime('%Y-%m-%d')
    end_date = today.strftime('%Y-%m-%d')

    # Daily Venus Report v1
    logger.info(f'Generating Daily report v1 from {start_date} to {end_date}')
    try:
        response, ingestion_results = r.get_report(start_date, end_date, 'daily', retrain=False)
        logger.info('Daily report v1 Processed.')
    except Exception as e:
        logger.error(f"Error Generating v1 report. {e}")

    # Daily Venus Report v2
    logger.info(f'Generating Daily report v2 from {start_date} to {end_date}')
    try:
        report_builder_v2.get_report(start_date, end_date, 'daily')
        logger.info('Daily report v2 Processed.')
    except Exception as e:
        logger.error(f"Error Generating v2 report. {e}")

    # Regular Cleaning up of celery_taskmeta tables
    r.cleanup_db_tables()

    return response


if __name__ == '__main__':
    main()
