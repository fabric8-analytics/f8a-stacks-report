"""Entry file for the main functionality."""

import logging
import json
from datetime import datetime as dt, timedelta, date
from report_helper import ReportHelper


logger = logging.getLogger(__file__)


def time_to_generate_monthly_report(today):
    """Check whether it is the right time to generate monthly report."""
    # We will make three attempts to generate the monthly report every month
    return today.day in (1, 2, 3, 26, 27, 28, 29)


def main():
    """Generate the weekly and monthly stacks report."""
    r = ReportHelper()
    today = dt.today()

    start_date = (today - timedelta(days=1)).strftime('%Y-%m-%d')
    end_date = today.strftime('%Y-%m-%d')
    response, ingestion_results = r.get_report(start_date, end_date, 'daily', retrain=False)
    logger.debug('Daily report data from {s} to {e}'.format(s=start_date, e=end_date))
    logger.debug(json.dumps(response, indent=2))
    logger.debug(json.dumps(ingestion_results, indent=2))

    # weekly re-training of models
    if today.weekday() >= 0:
        start_date_wk = (today - timedelta(days=7)).strftime('%Y-%m-%d')
        end_date_wk = today.strftime('%Y-%m-%d')
        r.re_train(start_date_wk, end_date_wk, 'weekly', retrain=True)

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
