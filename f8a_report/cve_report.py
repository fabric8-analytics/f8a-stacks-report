from datetime import datetime, timedelta
from enum import Enum
from typing import Union, Dict, Tuple
from victimsdb_lib import VictimsDB

import json
import logging
import random
import requests
import os
import tempfile

logger = logging.getLogger('CVEReport')
auth_header = None


class CVEReportError(Exception):
    pass


def get_auth_header():
    # type: () -> Union[Dict[str, str], None]
    """
    Return dictionary for use with requests library.
    The dictionary contains authorization token for Github API.
    """
    token = random.choice(os.environ.get('GITHUB_TOKEN', '').split(','))
    if token:
        return {'Authorization': 'token ' + token}
    else:
        return None


def github_request(url):
    # type: (str) -> Dict[str, str]
    """
    Send a request to the Github API.
    Return a tuple with status code and message body as a dictionary or None in case of any failure.
    """
    try:
        r = requests.get(url, headers=auth_header)
        if r.status_code == 200:
            body = r.json()
            return body
        else:
            logger.error("Communication with Github failed. Status code={}".format(r.status_code))
    except requests.RequestException as e:
        logger.exception(e)
    except json.decoder.JSONDecodeError:
        logger.error('Response for URL={} does not contain JSON object.'.format(url))

    raise CVEReportError


def download_and_save_file(from_url, to_path):
    try:
        r = requests.get(from_url)
        if r.status_code == 200:
            with open(to_path, 'w') as f:
                f.write(r.content)
    except requests.RequestException as e:
        logger.exception(e)


class ReportType(Enum):
    DAILY = 1,
    WEEKLY = 2,
    MONTHLY = 3,

    def generate_time_span(self):
        mapping = {
            ReportType.DAILY: 1,
            ReportType.WEEKLY: 7,
            ReportType.MONTHLY: 31,
        }
        delta = mapping[self]
        from_date = (datetime.today() - timedelta(days=delta)).strftime('%Y-%m-%d')
        till_date = datetime.today().strftime('%Y-%m-%d')
        return from_date, till_date


class Report:
    """Generic report that handles a dictionary and can store it to S3."""

    def __init__(self):
        self.report_data = dict()
        self.report_directory = None
        self.name = None  # TODO:
        # TODO: include the S3 helper?

    def store_to_s3(self):
        pass


class CVEReport(Report):

    def __init__(self):
        """Create an empty report."""
        super(CVEReport, self).__init__()

    @staticmethod
    def _parse_pr_title(title):
        parts = title.split(' ')
        ecosystem = parts[0][1:-1]
        cve = parts[2]
        return ecosystem, cve

    @staticmethod
    def _get_files(number):
        url = "https://api.github.com/repos/fabric8-analytics/cvedb/pulls/{}/files".format(number)
        body = github_request(url)
        return list(map(lambda x: x['raw_url'], body))

    @staticmethod
    def _process_item(item, temp_dir):
        ecosystem_in_title, cve_id = CVEReport._parse_pr_title(item['title'])
        number = item['number']
        raw_files = CVEReport._get_files(number)
        for file in raw_files:
            url_parts = file.split('/')
            ecosystem, year, filename = url_parts[-3], url_parts[-2], url_parts[-1]
            if ecosystem != ecosystem_in_title:
                logger.warning("PR={} title does not match with the yaml file.".format(number))

            to_file = '/'.join([temp_dir.name, ecosystem, year, filename])
            download_and_save_file(file, to_file)

    def generate_report(self, report_type):
        # type: (ReportType) -> None
        """Generate a report for the previous day/week/month.

        This method can fail in various ways, because it communicates with GH and S3. Make sure
        to handle exceptions.
        """
        from_date, till_date = report_type.generate_time_span()
        self.report_directory = None
        # TODO: ^^^--- fill in the data and call the functions ---vvv

    def generate_victimsdb(self, from_date, till_date):
        # type: (str, str) -> Union[None, VictimsDB]
        """Blah."""
        # https://api.github.com/search/issues?q=repo:fabric8-analytics/cvedb+type:pr+Add%20CVE-%20in:title+is:merged+merged:2019-02-01..2019-02-02
        url = "https://api.github.com/search/issues?q=repo:fabric8-analytics/"\
              "cvedb+type:pr+Add%20CVE-%20in:title+is:merged+merged:"\
              "{}..{}".format(from_date, till_date)
        body = github_request(url)
        try:
            items = body['items']
            with tempfile.TemporaryDirectory() as temp_dir:
                for item in items:
                    CVEReport._process_item(item, temp_dir)

                db = VictimsDB.from_dir(temp_dir.name)
                return db

        except KeyError:
            logger.error("Github response came in unexpected format (JSON structure is different).")
        except IndexError:
            logger.error("Github response came in unexpected format (JSON structure is different).")

        return None
