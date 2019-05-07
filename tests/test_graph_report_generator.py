"""Test module for classes and functions found in the report_generator module."""

from f8a_report.graph_report_generator import execute_gremlin_dsl, \
    generate_report_for_unknown_epvs, generate_report_for_latest_version, \
    generate_report_for_cves
from unittest import mock


def mock_response():
    """Generate data for mock response."""
    x = {
        "result": {
            "data": [
                {
                    "pecosystem": ["maven"],
                    "pname": ["io.vertx:vertx-web"],
                    "version": ["3.6.3"]
                }
            ]
        }

    }
    return x


def mock_response1():
    """Generate data for mock1 response."""
    x = {
        "result": {
            "data": [
                {
                    "ecosystem": ["maven"],
                    "name": ["io.vertx:vertx-web"],
                    "latest_version": ["3.6.3"]
                },
                {
                    "ecosystem": ["npm"],
                    "name": ["lodash"],
                    "latest_version": ["2.39.2"]
                }
            ]
        }

    }
    return x


def mock_response2():
    """Generate data for mock2 response."""
    x = {
        "result": {
            "data": [
                {
                    "a": {
                        "cve_id": [
                            "CVE-2013-4310"
                        ]
                    },
                    "b": {
                        "pname": [
                            "org.apache.struts:struts2-core"
                        ],
                        "version": [
                            "2.0.5"
                        ]
                    }
                },
                {
                    "a": {
                        "cve_id": [
                            "CVE-2013-4310"
                        ]
                    },
                    "b": {
                        "pname": [
                            "org.apache.struts:struts2-core"
                        ],
                        "version": [
                            "2.0.7"
                        ]
                    }
                }
            ]
        }

    }
    return x


@mock.patch("f8a_report.graph_report_generator.execute_gremlin_dsl")
def test_generate_report_for_unknown_epvs(mocker):
    """Test generate_report_for_unknown_epvs function."""
    mocker.return_value = mock_response()
    epv_list = [{
                    "ecosystem": "maven",
                    "name": "io.vertx:vertx-web",
                    "version": "3.6.3"
                },
                {
                    "ecosystem": "npm",
                    "name": "lodash",
                    "version": "2.40.1"
                }]
    out = generate_report_for_unknown_epvs(epv_list)
    assert out['maven@DELIM@io.vertx:vertx-web@DELIM@3.6.3'] == "true"
    assert out['npm@DELIM@lodash@DELIM@2.40.1'] == "false"


@mock.patch("f8a_report.graph_report_generator.execute_gremlin_dsl")
def test_generate_report_for_latest_version(mocker):
    """Test generate_report_for_latest_version function."""
    mocker.return_value = mock_response1()
    epv_list = [{
                    "ecosystem": "maven",
                    "name": "io.vertx:vertx-web"
                },
                {
                    "ecosystem": "npm",
                    "name": "lodash"
                },
                {
                    "ecosystem": "npm",
                    "name": "test-hooks"
                }]
    out = generate_report_for_latest_version(epv_list)
    assert out['maven@DELIM@io.vertx:vertx-web']['known_latest_version'] == "3.6.3"
    assert out['npm@DELIM@lodash']['known_latest_version'] == "2.39.2"
    assert out['maven@DELIM@io.vertx:vertx-web']['actual_latest_version'] is not None
    assert out['npm@DELIM@lodash']['actual_latest_version'] is not None


@mock.patch("f8a_report.graph_report_generator.execute_gremlin_dsl")
def test_generate_report_for_cves(mocker):
    """Test generate_report_for_cves function."""
    mocker.return_value = mock_response2()
    cve_data = {
        "CVE-2013-4310": {
            "ecosystem": "maven",
            "packages": [
                {
                    "name": "org.apache.struts:struts2-core",
                    "versions": ["2.0.5", "2.0.6"]
                }
            ]
        }
    }
    out = generate_report_for_cves(cve_data)
    assert out['CVE-2013-4310@DELIM@org.apache.struts:struts2-core@DELIM@2.0.5'] == \
        "Found"
    assert out['CVE-2013-4310@DELIM@org.apache.struts:struts2-core@DELIM@2.0.6'] == \
        "Not Found"
    assert out['CVE-2013-4310@DELIM@org.apache.struts:struts2-core@DELIM@2.0.7'] == \
        "False Positive"


@mock.patch('requests.Session.post', side_effect="")
def test_execute_gremlin_dsl(mocker):
    """Test the function execute_gremlin_dsl."""
    mocker.return_value = ""
    query_str = "g.V().has('ecosystem', eco).has('name',pkg).valueMap()"
    payload = {
        'gremlin': query_str,
        'bindings': {
            'eco': 'maven',
            'pkg': 'io.vertx:vertx-web'
        }
    }
    out = execute_gremlin_dsl(payload)
    assert out is None
