"""Tests Report Generator v2."""

import json
from unittest import TestCase
from f8a_report.v2.report_generator import ReportBuilderV2
from unittest.mock import patch


class TestReportBuilderV2(TestCase):
    """Test Namespace for Report Builder v2 Class."""

    @classmethod
    def setUp(cls):
        """Initialise class with required params."""
        cls._resource_paths = ['a', 'b']
        cls.ReportBuilder = ReportBuilderV2()
        with open('tests/data/stack_report_v2.json', 'r') as f:
            cls.stack_analyses_v2 = json.load(f)

    def test_normalize_deps_list(self):
        """Test Normalize deps list."""
        dependencies = self.stack_analyses_v2[0][0].get(
            'analyzed_dependencies')[0].get('dependencies')
        result = self.ReportBuilder.normalize_deps_list(dependencies)
        self.assertIsInstance(result, list)
        self.assertListEqual(['python-dateutil 2.7.3', 'six 1.12.0'], result)

    def test_get_report_template(self):
        """Test Normalize deps list."""
        start_date = "01-01-2020"
        end_date = "05-01-2020"
        result = self.ReportBuilder.get_report_template(start_date, end_date)
        self.assertIsInstance(result, dict)
        self.assertIn("report", result)

    def test_get_analysed_dependencies(self):
        """Test Analyses Dependencies."""
        stack = self.stack_analyses_v2[0][0]
        result = self.ReportBuilder.get_analysed_dependencies(stack)
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)

    def test_normalized_unknown_dependencies(self):
        """Test Normalized Dependencies."""
        result = self.ReportBuilder.normalized_unknown_dependencies(self.stack_analyses_v2[6][0])
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 47)

    def test_get_stack_info_template(self):
        """Test Stack Info Template."""
        result = self.ReportBuilder.get_stack_info_template()
        self.assertIsInstance(result, dict)
        self.assertIn('ecosystem', result)
        self.assertIn('unknown_dependencies', result)
        self.assertIn('license', result)
        self.assertIn('public_vulnerabilities', result)
        self.assertIn('private_vulnerabilities', result)
        self.assertIn('response_time', result)

    def test_get_unknown_licenses(self):
        """Test Get Unknown Licenses."""
        stack = self.stack_analyses_v2[0][0]
        result = self.ReportBuilder.get_unknown_licenses(stack)
        self.assertEqual(len(result), 2)

    def test_get_ecosystem(self):
        """Test Get Ecosystem."""
        stack = self.stack_analyses_v2[0][0]
        result = self.ReportBuilder.get_ecosystem(stack)
        self.assertEqual(result, 'pypi')

    def test_audit_timelines(self):
        """Test Audit Time-lines."""
        stack = self.stack_analyses_v2[0][0]
        started_at, ended_at = self.ReportBuilder.get_audit_timelines(stack)
        self.assertEqual(ended_at, '2020-05-27T07:44:57.181500')
        self.assertEqual(started_at, '2020-05-27T07:44:56.968213')

    def test_analyse_stack(self):
        """Test Analyse Stack."""
        start_date = "01-01-2020"
        end_date = "05-01-2020"
        stack = self.stack_analyses_v2
        report_template = self.ReportBuilder.get_report_template(start_date, end_date)
        result = self.ReportBuilder.analyse_stack(stack, report_template)
        self.assertIn('report', result)
        self.assertIn('stacks_summary', result)
        self.assertIn('stacks_details', result)
        self.assertGreater(len('stacks_details'), 0)
        self.assertGreater(len('stacks_summary'), 0)

    def test_analyse_stack_with_no_analyse_dep(self):
        """Test Analyse Stack with No Analyses Dependencies."""
        start_date = "01-01-2020"
        end_date = "05-01-2020"
        stack = [self.stack_analyses_v2[3]]
        report_template = self.ReportBuilder.get_report_template(start_date, end_date)
        result = self.ReportBuilder.analyse_stack(stack, report_template)
        self.assertIn('report', result)
        self.assertIn('stacks_summary', result)
        self.assertIn('stacks_details', result)
        self.assertGreater(len('stacks_details'), 0)
        self.assertGreater(len('stacks_summary'), 0)

    @patch('f8a_report.v2.report_generator.ReportBuilderV2.build_report_summary')
    @patch('f8a_report.v2.report_generator.ReportBuilderV2.save_result', return_value=True)
    @patch('f8a_report.v2.report_generator.ReportBuilderV2.save_ingestion_report_in_s3')
    @patch('f8a_report.v2.report_generator.UnknownDepsReportHelper.get_current_ingestion_status')
    def test_normalize_worker_data(self, _mock1, _mock2, _mock3, _mock4):
        """Test Normalize worker data."""
        stacks_data = json.dumps(self.stack_analyses_v2)
        _mock2.return_value = True
        self.ReportBuilder.start_date = "2020-01-01"
        self.ReportBuilder.end_date = "2020-01-02"
        with open('tests/data/unknown_dependencies.json', 'r') as f:
            _mock1.return_value = json.load(f)
        with open('tests/data/report_summary.json', 'r') as f:
            _mock4.return_value = json.load(f)

        result = self.ReportBuilder.normalize_worker_data(stacks_data, False)
        self.assertIn('daily', result)
        self.assertIn('stacks_summary', result[2])

    @patch('f8a_report.v2.report_generator.ReportBuilderV2.check_latest_node')
    @patch('f8a_report.v2.report_generator.generate_report_for_unknown_epvs')
    @patch('f8a_report.v2.report_generator.generate_report_for_latest_version')
    @patch('f8a_report.v2.report_generator.UnknownDepsReportHelper.get_current_ingestion_status')
    def test_normalize_ingestion_data(self, _mock1, _mock2, _mock3, _mock4):
        """Test Normalize Ingestion data."""
        _mock4.return_value = "content"
        start_date = "2020-01-01"
        end_date = "2020-01-02"
        ingestion_data = {'EPV_DATA': json.dumps({})}
        result = self.ReportBuilder.normalize_ingestion_data(start_date, end_date, ingestion_data)
        self.assertEqual(result, 'content')

    @patch('f8a_report.v2.report_generator.ReportBuilderV2.save_ingestion_report_in_s3')
    @patch('f8a_report.v2.report_generator.ReportBuilderV2.save_result')
    @patch('f8a_report.v2.report_generator.ReportBuilderV2.normalize_worker_data')
    @patch('f8a_report.v2.report_generator.ReportQueries.get_worker_results_v2')
    @patch('f8a_report.v2.report_generator.SentryReportHelper.retrieve_sentry_logs')
    @patch('f8a_report.v2.report_generator.ReportBuilderV2.normalize_ingestion_data')
    @patch('f8a_report.v2.report_generator.ReportQueries.retrieve_ingestion_results')
    @patch('f8a_report.v2.report_generator.ReportQueries.retrieve_stack_analyses_ids')
    def test_get_report(self, _mock1, _mock2, _mock3, _mock4, _mock5, _mock6, _mock7, _mock8):
        """Test Get data."""
        _mock1.return_value = ('09aa6480a3ce477881109d9635c30257',)
        _mock2.return_value = {}
        _mock4.return_value = "not-none"
        _mock5.return_value = {}
        start_date = "2020-01-01"
        end_date = "2020-01-02"
        with open('tests/data/normalised_ingestion_data.json', 'r') as f:
            _mock3.return_value = json.load(f)
        with open('tests/data/normalised_worker_data.json', 'r') as f:
            _mock6.return_value = json.load(f)

        result = self.ReportBuilder.get_report(start_date, end_date)
        self.assertIn('stack_aggregator_v2', result[0])
        self.assertEqual(
            result[0]['stack_aggregator_v2']['stacks_summary']['total_stack_requests_count'], 10)

    @patch('f8a_report.v2.report_generator.S3Helper.store_json_content')
    def test_save_result(self, _mock1):
        """Test save to s3."""
        result = self.ReportBuilder.save_result('daily', 'report_name', 'content')
        self.assertTrue(result)
