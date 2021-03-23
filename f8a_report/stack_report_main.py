"""Daily stacks report."""

import logging
from datetime import datetime as dt, timedelta

from f8a_report.helpers.report_helper import ReportHelper
from f8a_report.helpers.sentry_report_helper import generate_sentry_report
from f8a_report.v2.report_generator import StackReportBuilder
from f8a_report.helpers.ingestion_helper import ingest_epv, generate_ingestion_report

logger = logging.getLogger(__file__)


def main():
    """Generate the daily stacks report."""
    report_builder_v2 = StackReportBuilder(ReportHelper)
    today = dt.today()
    start_date = (today - timedelta(days=100)).strftime('%Y-%m-%d')
    end_date = today.strftime('%Y-%m-%d')
    missing_latest_nodes = {}
    response = {}

    # Generate Ingestion Report and save in S3
    generate_ingestion_report(start_date, end_date)

    # Generate Sentry Report and save in S3
    generate_sentry_report(start_date, end_date)

    # Daily Venus Report v2
    logger.info('Generating Daily report v2 from %s to %s', start_date, end_date)
    try:
        report_builder_v2.get_report(start_date, end_date, 'daily')
        logger.info('Daily report v2 Processed.')
    except Exception as e:
        logger.exception("Error Generating v2 report")
        raise e

    # After all the reports are generated,
    # trigger ingestion flow for the packages which are missing a version from Graph DB.
    ingest_epv(missing_latest_nodes)

    return response


if __name__ == '__main__':
    main()
