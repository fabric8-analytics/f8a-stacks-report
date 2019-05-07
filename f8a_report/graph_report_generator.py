"""Helper functions related to to generate ingestion reports."""

from f8a_utils.versions import get_latest_versions_for_ep
import logging
import os
import requests
import traceback
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

_logger = logging.getLogger(__name__)

GREMLIN_SERVER_URL_REST = "http://{host}:{port}".format(
    host=os.environ.get("BAYESIAN_GREMLIN_HTTP_SERVICE_HOST", "localhost"),
    port=os.environ.get("BAYESIAN_GREMLIN_HTTP_SERVICE_PORT", "8182"))

GREMLIN_QUERY_SIZE = int(os.getenv('GREMLIN_QUERY_SIZE', 50))


def generate_report_for_cves(cve_data):
    """Generate a report for CVEs.

    :param cve_data: list, list of CVEs
    :return json, list of cve information
    """
    query_str = "g.V().has('cecosystem', '{arg0}')." \
                "has('cve_id', '{arg1}').as('a').in('has_cve').as('b')." \
                "select('a','b').by(valueMap('cve_id', 'pname', 'version'))." \
                "dedup().fill(epv);"
    report_result = {}
    args = []
    for k, v in cve_data.items():
        eco = v['ecosystem']
        args.append({
            "0": eco,
            "1": k
        })
        for pkg in v['packages']:
            name = pkg['name']
            for ver in pkg['versions']:
                key = k + "@DELIM@" + name + "@DELIM@" + ver
                report_result[key] = "Not Found"
    result_data = batch_query_executor(query_str, args)
    if result_data is not None:
        for res in result_data:
            id = get_value(res['a'], 'cve_id') if 'a' in res else ""
            pkg = get_value(res['b'], 'pname') if 'b' in res else ""
            ver = get_value(res['b'], 'version') if 'b' in res else ""
            key = id + "@DELIM@" + pkg + "@DELIM@" + ver
            if key in report_result:
                report_result[key] = "Found"
            else:
                report_result[key] = "False Positive"
    return report_result


def generate_report_for_unknown_epvs(epv_list):
    """Generate a report for the unknown EPVs.

    :param epv_list: list, list of EPVs
    :return json, list of epv information
    """
    query_str = "g.V().has('pecosystem', '{arg0}')." \
                "has('pname', '{arg1}').has('version', '{arg2}')" \
                ".valueMap().dedup().fill(epv);"
    report_result = {}
    args = []
    for epv in epv_list:
        eco = epv['ecosystem']
        pkg = epv['name']
        ver = epv['version']
        args.append({
            "0": eco,
            "1": pkg,
            "2": ver
        })
        report_result[eco + "@DELIM@" + pkg + "@DELIM@" + ver] = "false"

    result_data = batch_query_executor(query_str, args)
    if result_data is not None:
        for res in result_data:
            eco = get_value(res, 'pecosystem')
            pkg = get_value(res, 'pname')
            ver = get_value(res, 'version')
            report_result[eco + "@DELIM@" + pkg + "@DELIM@" + ver] = "true"
    return report_result


def generate_report_for_latest_version(epv_list):
    """Generate a report for the latest version.

    :param epv_list: list, list of EPVs
    :return json, list of version information
    """
    query_str = "g.V().has('ecosystem', '{arg0}')." \
                "has('name', '{arg1}')" \
                ".valueMap().dedup().fill(epv);"
    report_result = {}
    args = []
    for epv in epv_list:
        eco = epv['ecosystem']
        pkg = epv['name']
        args.append({
            "0": eco,
            "1": pkg
        })
        latest = get_latest_versions_for_ep(eco, pkg)
        tmp = {
            "ecosystem": eco,
            "name": pkg,
            "known_latest_version": "",
            "actual_latest_version": latest
        }
        report_result[eco + "@DELIM@" + pkg] = tmp

    result_data = batch_query_executor(query_str, args)
    if result_data is not None:
        for res in result_data:
            eco = get_value(res, 'ecosystem')
            pkg = get_value(res, 'name')
            latest_pkg_version = get_value(res, 'latest_version')
            report_result[eco + "@DELIM@" + pkg]['known_latest_version'] = latest_pkg_version

    return report_result


def execute_gremlin_dsl(payload, url=GREMLIN_SERVER_URL_REST):
    """Execute the gremlin query and return the response."""
    try:
        response = get_session_retry().post(url, json=payload)
        if response.status_code == 200:
            return response.json()
        else:
            _logger.error(
                "HTTP error {code}. Error retrieving data from {url}.".format(
                    code=response.status_code, url=url))
            return None

    except Exception:
        _logger.error(traceback.format_exc())
        return None


def get_session_retry(retries=3, backoff_factor=0.2, status_forcelist=(404, 500, 502, 504),
                      session=None):
    """Set HTTP Adapter with retries to session."""
    session = session or requests.Session()
    retry = Retry(total=retries, read=retries, connect=retries,
                  backoff_factor=backoff_factor, status_forcelist=status_forcelist)
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    return session


def get_response_data(json_response, data_default):
    """Retrieve data from the JSON response.

    Data default parameters takes what should data to be returned.
    """
    return json_response.get("result", {}).get("data", data_default)


def get_value(json, attr):
    """Get the value from the json."""
    if attr in json:
        return json[attr][0]
    return ""


def batch_query_executor(query_string, args):
    """Execute the gremlin query in batches of 50."""
    query = "epv=[];"
    tmp_query = ""
    counter = 0
    result_data = []
    for arg in args:
        if len(arg) == 2:
            tmp_query = query_string.format(arg0=arg['0'], arg1=arg['1'])
            counter += 1
        elif len(arg) == 3:
            tmp_query = query_string.format(arg0=arg['0'], arg1=arg['1'], arg2=arg['2'])
            counter += 1
        if counter == 1:
            query = "epv=[];"
        query += tmp_query

        if counter >= GREMLIN_QUERY_SIZE:
            counter = 0
            payload = {'gremlin': query}
            gremlin_response = execute_gremlin_dsl(payload)
            if gremlin_response is not None:
                result_data += get_response_data(gremlin_response, [{0: 0}])
            else:
                _logger.error("Error while trying to fetch data from graph. "
                              "Expected response, got None...Query->", query)

    if counter < GREMLIN_QUERY_SIZE:
        payload = {'gremlin': query}
        gremlin_response = execute_gremlin_dsl(payload)
        if gremlin_response is not None:
            result_data += get_response_data(gremlin_response, [{0: 0}])
        else:
            _logger.error("Error while trying to fetch data from graph. "
                          "Expected response, got None...Query->", query)

    return result_data
