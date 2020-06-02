"""Entry file for the main functionality."""

import logging
import json
from datetime import datetime as dt, timedelta, date
from report_helper import ReportHelper
from v2.report_generator import ReportBuilderV2
from manifest_helper import manifest_interface
import os


logger = logging.getLogger(__file__)


def time_to_generate_monthly_report(today):
    """Check whether it is the right time to generate monthly report."""
    # We will make three attempts to generate the monthly report every month
    return today.day in (1, 2, 3)


def main():
    """Generate the weekly and monthly stacks report."""
    r = ReportHelper()
    r2 = ReportBuilderV2()
    today = dt.today()
    start_date = (today - timedelta(days=1)).strftime('%Y-%m-%d')
    end_date = today.strftime('%Y-%m-%d')

    # Generate daily venus report
    response, ingestion_results = r.get_report(start_date, end_date, 'daily', retrain=False)
    response_v2, ingestion_results_v2 = r2.get_report(start_date, end_date, 'daily', retrain=False)
    logger.debug('Daily report data from {s} to {e}'.format(s=start_date, e=end_date))
    logger.debug(json.dumps(response, indent=2))
    logger.debug(json.dumps(ingestion_results, indent=2))

    # Regular Cleaning up of celery_taskmeta tables
    r.cleanup_db_tables()
    # Weekly re-training of models
    start_date_wk = (today - timedelta(days=7)).strftime('%Y-%m-%d')
    end_date_wk = today.strftime('%Y-%m-%d')
    if today.weekday() == 0:
        logger.info('Weekly Job Triggered')
        try:
            r.re_train(start_date_wk, end_date_wk, 'weekly', retrain=True)
        except Exception as e:
            logger.error("Exception in Retraining {}".format(e))
            pass
        logger.info(os.environ.get('GENERATE_MANIFESTS', 'False'))
        if os.environ.get('GENERATE_MANIFESTS', 'False') in ('True', 'true', '1'):
            logger.info('Generating Manifests based on last 1 week Stack Analyses calls.')
            stacks = r.retrieve_stack_analyses_content(start_date_wk, end_date_wk)
            manifest_interface(stacks)

    # Generate a monthly venus report
    if time_to_generate_monthly_report(today):
        last_day_of_prev_month = date(today.year, today.month, 1) - timedelta(days=1)
        last_month_first_date = last_day_of_prev_month.strftime('%Y-%m-01')
        last_month_end_date = last_day_of_prev_month.strftime('%Y-%m-%d')
        response, ingestion_results = r.get_report(last_month_first_date,
                                                   last_month_end_date,
                                                   'monthly', retrain=False)
        logger.debug('Monthly report data from {s} to {e}'.format(s=start_date, e=end_date))
        logger.debug(json.dumps(response, indent=2))

    return response


if __name__ == '__main__':
    main()
