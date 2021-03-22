"""Functions to handle worker related tasks."""

import logging
import os
from typing import Dict
import requests
import tenacity

from helpers.db_gateway import ReportQueries
from helpers.report_helper import ReportHelper

logger = logging.getLogger(__file__)

_APP_SECRET_KEY = os.getenv('APP_SECRET_KEY', 'not-set')
_INGESTION_API_URL = "http://{host}:{port}/{endpoint}".format(
    host=os.environ.get("INGESTION_SERVICE_HOST", "bayesian-jobs"),
    port=os.environ.get("INGESTION_SERVICE_PORT", "34000"),
    endpoint='ingestions/epv')


@tenacity.retry(reraise=True, stop=tenacity.stop_after_attempt(3), wait=tenacity.wait_fixed(1))
def ingest_epv(missing_latest_nodes):
    """
    Initialize Selinon workers.

    If report has packages which are missing any version from Db, ingestion flow
    for such packages will be triggered to ingest requested version into Graph DB
    using Jobs API.
    """
    try:
        result = {}
        # Iterate through ecosystems.
        for ecosystem, packages in missing_latest_nodes.items():
            # Prepare input data in required format.
            request_data = {
                'ecosystem': ecosystem,
                'packages': packages
            }

            logger.info("Invoking service for triggering ingestion flow for missing_latest_node")

            # Make API call and set token which will be used for authentication.
            response = requests.post(_INGESTION_API_URL, json=request_data,
                                     headers={'auth_token': _APP_SECRET_KEY})

            logger.info("Ingestion API status_code: {} "
                        "and response: {}".format(response.status_code, response.json()))

            result[ecosystem] = {
                'status_code': response.status_code,
                'result': response.json()
            }
    except Exception as e:
        logger.error("Error while ingesting missing versions {}".format(e))

    return result


def generate_ingestion_report(start_date: str, end_date: str, frequency='daily') -> Dict:
    """Collect Ingestion data from Database and generates Report out of it.

    :param frequency: daily/monthly
    :param start_date: Start date of Ingestion data
    :param end_date: End date of Ingestion data

    :returns: Ingestion Results dump
    """
    rds_obj = ReportQueries()

    # Query DB to fetch ingestion data
    ingestion_db_data = rds_obj.retrieve_ingestion_results(start_date, end_date)
    if not ingestion_db_data:
        logger.error('No Ingestion data found in last 24 hours')

    result = {'EPV_DATA': ingestion_db_data}
    # Generate Ingestion Report
    ingestion_result, _ = ReportHelper().normalize_ingestion_data(
        start_date, end_date, result, frequency)
    return ingestion_result
