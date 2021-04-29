"""Tests Report Generator v2."""

import json
from unittest import TestCase
from f8a_report.v2.report_generator import StackReportBuilder
from f8a_report.helpers.report_helper import ReportHelper
from unittest.mock import patch


class TestStackReportBuilder(TestCase):
    """Test Namespace for Report Builder v2 Class."""

    @classmethod
    def setUp(cls):
        """Initialise class with required params."""
        cls.ReportBuilder = StackReportBuilder(ReportHelper)
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

    def test_get_unknown_licenses(self):
        """Test Get Unknown Licenses."""
        stack = self.stack_analyses_v2[0][0]
        result = self.ReportBuilder.get_unknown_licenses(stack)
        self.assertEqual(len(result), 2)

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
        self.assertGreater(len('stacks_summary'), 0)

    @patch('f8a_report.v2.report_generator.StackReportBuilder.create_venus_report')
    @patch('f8a_report.v2.report_generator.StackReportBuilder.save_worker_result_to_s3')
    @patch('f8a_report.v2.report_generator.StackReportBuilder.normalize_worker_data')
    @patch('f8a_report.v2.report_generator.ReportQueries.get_worker_results_v2')
    @patch('f8a_report.v2.report_generator.ReportQueries.retrieve_stack_analyses_ids')
    def test_get_report(self, _mock1, _mock2, _mock3, _mock4, _mock5):
        """Test Get data."""
        _mock1.return_value = ('09aa6480a3ce477881109d9635c30257',)
        _mock4.return_value = {}
        start_date = "2020-01-01"
        end_date = "2020-01-02"
        with open('tests/data/normalised_worker_data.json', 'r') as f:
            generated_report = json.load(f)
            _mock3.return_value = generated_report
            _mock5.return_value = generated_report[2]

        result = self.ReportBuilder.get_report(start_date, end_date)
        self.assertIn('stack_aggregator_v2', result)
        self.assertEqual(
            result['stack_aggregator_v2']['stacks_summary']['total_stack_requests_count'], 10)

    @patch('f8a_report.v2.report_generator.S3Helper.store_json_content')
    def test_save_result(self, _mock1):
        """Test save to s3."""
        result = self.ReportBuilder.save_worker_result_to_s3('daily', 'report_name', 'content')
        self.assertTrue(result)

    @patch('f8a_report.v2.report_generator.StackReportBuilder.create_venus_report')
    @patch('f8a_report.v2.report_generator.StackReportBuilder.save_worker_result_to_s3')
    @patch('f8a_report.v2.report_generator.StackReportBuilder.normalize_worker_data')
    @patch('f8a_report.v2.report_generator.ReportQueries.get_worker_results_v2')
    @patch('f8a_report.v2.report_generator.ReportQueries.retrieve_stack_analyses_ids')
    def test_get_report_for_golang(self, _mock1, _mock2, _mock3, _mock4, _mock5):
        """Test Entrypoint for Venus Reporting v2 Golang."""
        _mock1.return_value = ('09aa6480a3ce477881109d9635c30257',)
        _mock4.return_value = {}
        start_date = "2020-01-01"
        end_date = "2020-01-02"
        with open('tests/data/normalised_worker_data_with_golang.json', 'r') as f:
            generated_report = json.load(f)
            _mock3.return_value = generated_report
            _mock5.return_value = generated_report[2]
        result = self.ReportBuilder.get_report(start_date, end_date)
        self.assertIn('stack_aggregator_v2', result)
        self.assertEqual(
                result['stack_aggregator_v2']['stacks_summary']
                ['total_stack_requests_count'], 1)
        self.assertEqual(
            result['stack_aggregator_v2']['stacks_summary']['golang']
            ['stack_requests_count'], 1)
        self.assertEqual(
            result['stack_aggregator_v2']['stacks_details']
            [0]['stack'][0], "github.com/thoughtworks/talisman 0.3.3")
