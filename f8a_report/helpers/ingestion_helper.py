"""Functions to handle worker related tasks."""

import logging
import os
import requests

logger = logging.getLogger(__file__)

_APP_SECRET_KEY = os.getenv('APP_SECRET_KEY', 'not-set')
_INGESTION_API_URL = "http://{host}:{port}/{endpoint}".format(
    host=os.environ.get("INGESTION_SERVICE_HOST", "bayesian-jobs"),
    port=os.environ.get("INGESTION_SERVICE_PORT", "34000"),
    endpoint='ingestions/ingest-epv')


def ingest_epv(missing_latest_nodes):
    """
    Initialize Selinon workers.

    If report has packages which are missing any version from Db, ingestion flow
    for such packages will be triggered to ingest requested version into Graph DB
    using Jobs API.
    """
    try:
        logger.info("Invoking service for triggering ingestion flow for missing_latest_node")

        # Make API call and set token which will be used for authentication.
        response = requests.post(_INGESTION_API_URL, json=missing_latest_nodes,
                                 headers={'auth_token': _APP_SECRET_KEY})

        logger.info("Ingestion API status_code: {} "
                    "and response: {}".format(response.status_code, response.json()))
    except Exception as e:
        logger.error("Error while ingesting missing versions {}".format(e))
