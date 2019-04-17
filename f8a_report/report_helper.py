"""Various utility functions used across the repo."""

import os
import json
import logging
import psycopg2
import psycopg2.extras
import itertools
import boto3
import requests
from datetime import datetime as dt
from psycopg2 import sql
from collections import Counter
from botocore.exceptions import ClientError
from graph_report_generator import generate_report_for_unknown_epvs,\
    generate_report_for_latest_version

logger = logging.getLogger(__file__)


class Postgres:
    """Postgres connection session handler."""

    def __init__(self):
        """Initialize the connection to Postgres database."""
        conn_string = "host='{host}' dbname='{dbname}' user='{user}' password='{password}'".\
            format(host=os.getenv('PGBOUNCER_SERVICE_HOST', 'bayesian-pgbouncer'),
                   dbname=os.getenv('POSTGRESQL_DATABASE', 'coreapi'),
                   user=os.getenv('POSTGRESQL_USER', 'coreapi'),
                   password=os.getenv('POSTGRESQL_PASSWORD', 'coreapi'))
        self.conn = psycopg2.connect(conn_string)
        self.cursor = self.conn.cursor()


class S3Helper:
    """Helper class for storing reports to S3."""

    def __init__(self):
        """Init method for the helper class."""
        self.region_name = os.environ.get('AWS_S3_REGION') or 'us-east-1'
        self.aws_s3_access_key = os.environ.get('AWS_S3_ACCESS_KEY_ID')
        self.aws_s3_secret_access_key = os.environ.get('AWS_S3_SECRET_ACCESS_KEY')
        self.deployment_prefix = os.environ.get('DEPLOYMENT_PREFIX') or 'dev'
        self.report_bucket_name = os.environ.get('REPORT_BUCKET_NAME')

        if self.aws_s3_secret_access_key is None or self.aws_s3_access_key is None or\
                self.region_name is None or self.deployment_prefix is None:
            raise ValueError("AWS credentials or S3 configuration was "
                             "not provided correctly. Please set the AWS_S3_REGION, "
                             "AWS_S3_ACCESS_KEY_ID, AWS_S3_SECRET_ACCESS_KEY, REPORT_BUCKET_NAME "
                             "and DEPLOYMENT_PREFIX correctly.")
        # S3 endpoint URL is required only for local deployments
        self.s3_endpoint_url = os.environ.get('S3_ENDPOINT_URL') or 'http://localhost'

        self.s3 = boto3.resource('s3', region_name=self.region_name,
                                 aws_access_key_id=self.aws_s3_access_key,
                                 aws_secret_access_key=self.aws_s3_secret_access_key)

    def store_json_content(self, content, bucket_name, obj_key):
        """Store the report content to the S3 storage."""
        try:
            logger.info('Storing the report into the S3 file %s' % obj_key)
            self.s3.Object(bucket_name, obj_key).put(
                Body=json.dumps(content, indent=2).encode('utf-8'))
        except Exception as e:
            logger.exception('%r' % e)

    def read_json_object(self, bucket_name, obj_key):
        """Get the report json object found on the S3 bucket."""
        try:
            obj = self.s3.Object(bucket_name, obj_key)
            result = json.loads(obj.get()['Body'].read().decode('utf-8'))
            return result
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                logger.exception('No Such Key %s exists' % obj_key)
            elif e.response['Error']['Code'] == 'NoSuchBucket':
                logger.exception('ERROR - No Such Bucket %s exists' % bucket_name)
            else:
                logger.exception('%r' % e)
            return None

    def list_objects(self, bucket_name, frequency):
        """Fetch the list of objects found on the S3 bucket."""
        prefix = '{dp}/{freq}'.format(dp=self.deployment_prefix, freq=frequency)
        res = {'objects': []}

        try:
            for obj in self.s3.Bucket(bucket_name).objects.filter(Prefix=prefix):
                if os.path.basename(obj.key) != '':
                    res['objects'].append(obj.key)
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                logger.exception('ERROR - No Such Key %s exists' % prefix)
            elif e.response['Error']['Code'] == 'NoSuchBucket':
                logger.exception('ERROR - No Such Bucket %s exists' % bucket_name)
            else:
                logger.exception('%r' % e)

        return res


class ReportHelper:
    """Stack Analyses report helper functions."""

    def __init__(self):
        """Init method for the Report helper class."""
        self.s3 = S3Helper()
        self.pg = Postgres()
        self.conn = self.pg.conn
        self.cursor = self.pg.cursor
        self.npm_model_bucket = os.getenv('NPM_MODEL_BUCKET', 'cvae-insights')
        self.maven_model_bucket = os.getenv('MAVEN_MODEL_BUCKET', 'hpf-insights')
        self.pypi_model_bucket = os.getenv('PYPI_MODEL_BUCKET', 'hpf-insights')
        self.golang_model_bucket = os.getenv('GOLANG_MODEL_BUCKET', 'golang-insights')
        self.maven_training_repo = os.getenv(
            'MAVEN_TRAINING_REPO', 'https://github.com/fabric8-analytics/f8a-hpf-insights')
        self.npm_training_repo = os.getenv(
            'NPM_TRAINING_REPO',
            'https://github.com/fabric8-analytics/fabric8-analytics-npm-insights')
        self.golang_training_repo = os.getenv(
            'GOLANG_TRAINING_REPO', 'https://github.com/fabric8-analytics/f8a-golang-insights')
        self.pypi_training_repo = os.getenv(
            'PYPI_TRAINING_REPO', 'https://github.com/fabric8-analytics/f8a-pypi-insights')

        self.emr_api = os.getenv('EMR_API', 'http://f8a-emr-deployment:6006')

    def validate_and_process_date(self, some_date):
        """Validate the date format and apply the format YYYY-MM-DDTHH:MI:SSZ."""
        try:
            dt.strptime(some_date, '%Y-%m-%d')
        except ValueError:
            raise ValueError("Incorrect data format, should be YYYY-MM-DD")
        return some_date

    def retrieve_stack_analyses_ids(self, start_date, end_date):
        """Retrieve results for stack analyses requests."""
        try:
            start_date = self.validate_and_process_date(start_date)
            end_date = self.validate_and_process_date(end_date)
        except ValueError:
            raise ValueError("Invalid date format")

        query = sql.SQL('SELECT {} FROM {} WHERE {} BETWEEN \'%s\' AND \'%s\'').format(
            sql.Identifier('id'), sql.Identifier('stack_analyses_request'),
            sql.Identifier('submitTime')
        )
        self.cursor.execute(query.as_string(self.conn) % (start_date, end_date))

        rows = self.cursor.fetchall()

        id_list = []
        for row in rows:
            for col in row:
                id_list.append(col)

        return id_list

    def flatten_list(self, alist):
        """Convert a list of lists to a single list."""
        return list(itertools.chain.from_iterable(alist))

    def datediff_in_millisecs(self, start_date, end_date):
        """Return the difference of two datetime strings in milliseconds."""
        format = '%Y-%m-%dT%H:%M:%S.%f'
        return (dt.strptime(end_date, format) -
                dt.strptime(start_date, format)).microseconds / 1000

    def populate_key_count(self, in_list=[]):
        """Generate a dict with the frequency of list elements."""
        out_dict = {}
        try:
            for item in in_list:
                if type(item) == dict:
                    logger.error('Unexpected key encountered %r' % item)
                    continue

                if item in out_dict:
                    out_dict[item] += 1
                else:
                    out_dict[item] = 1
        except (IndexError, KeyError, TypeError) as e:
            logger.exception('Error: %r' % e)
            return {}
        return out_dict

    def set_unique_stack_deps_count(self, unique_stacks_with_recurrence_count):
        """Set the dependencies count against the identified unique stacks."""
        out_dict = {}
        for key in unique_stacks_with_recurrence_count.items():
            new_dict = {}
            for stack in key[1].items():
                new_dict[stack[0]] = len(stack[0].split(','))
            out_dict[key[0]] = new_dict
        return out_dict

    def normalize_deps_list(self, deps):
        """Flatten the dependencies dict into a list."""
        normalized_list = []
        for dep in deps:
            normalized_list.append('{package} {version}'.format(package=dep['package'],
                                                                version=dep['version']))
        return sorted(normalized_list)

    def collate_raw_data(self, unique_stacks_with_recurrence_count, frequency):
        """Collate previous raw data with this week/month data."""
        result = {}

        # Get collated user input data
        collated_user_input_obj_key = '{depl_prefix}/user-input-data/collated-{freq}.json'.format(
            depl_prefix=self.s3.deployment_prefix, freq=frequency)
        collated_user_input = self.s3.read_json_object(bucket_name=self.s3.report_bucket_name,
                                                       obj_key=collated_user_input_obj_key) or {}

        for eco in unique_stacks_with_recurrence_count.keys() | collated_user_input.keys():
            result.update({eco: {
                "user_input_stack": dict(
                            Counter(unique_stacks_with_recurrence_count.get(eco)) +
                            Counter(collated_user_input.get(eco, {}).get('user_input_stack')))
            }})

        # Store user input collated data back to S3
        self.s3.store_json_content(content=result, bucket_name=self.s3.report_bucket_name,
                                   obj_key=collated_user_input_obj_key)

        # Get collated big query data
        collated_big_query_obj_key = '{depl_prefix}/big-query-data/collated.json'.format(
            depl_prefix=self.s3.deployment_prefix)
        collated_big_query_data = self.s3.read_json_object(bucket_name=self.s3.report_bucket_name,
                                                           obj_key=collated_big_query_obj_key) or {}

        for eco in collated_big_query_data.keys():
            if result.get(eco):
                result[eco]["bigquery_data"] = collated_big_query_data.get(eco)
            else:
                result[eco] = {"bigquery_data": collated_big_query_data.get(eco)}
        return result

    def invoke_emr_api(self, bucket_name, ecosystem, data_version, github_repo):
        """Invoke EMR Retraining API to start the retraining process."""
        payload = {
            'bucket_name': bucket_name,
            'github_repo': github_repo,
            'ecosystem': ecosystem,
            'data_version': data_version
        }

        try:
            # Invoke EMR API to run the retraining
            resp = requests.post(url=self.emr_api + '/api/v1/runjob', json=payload)
            # Check for status code
            # If status is not success, log it as an error
            if resp.status_code == 200:
                logger.info('Successfully invoked EMR API for {eco} ecosystem \n {resp}'.format(
                    eco=ecosystem, resp=resp.json()))
            else:
                logger.error('Error received from EMR API for {eco} ecosystem \n {resp}'.format(
                    eco=ecosystem, resp=resp.json()))
        except Exception:
            logger.error('Failed to invoke EMR API for {eco} ecosystem'.format(eco=ecosystem))

    def store_training_data(self, result):
        """Store Training Data for each ecosystem in their respective buckets."""
        model_version = dt.now().strftime('%Y-%m-%d')

        for eco, stack_dict in result.items():
            unique_stacks = {}
            obj_key = '{eco}/{depl_prefix}/{model_version}/data/manifest.json'.format(
                eco=eco, depl_prefix=self.s3.deployment_prefix, model_version=model_version)
            package_dict_for_eco = {
                "user_input_stack": [],
                "bigquery_data": []
            }
            for stack_type, stacks in stack_dict.items():
                package_list = [x.strip().split(' ')[0] for package in stacks
                                for x in package.split(',')]
                stack_str = "".join(package_list)
                if stack_str not in unique_stacks:
                    unique_stacks[stack_str] = 1
                    package_dict_for_eco.get(stack_type).append(package_list)

            training_data = {
                'ecosystem': eco,
                'package_dict': package_dict_for_eco
            }

            # Get the bucket name based on ecosystems to store user-input stacks for retraining
            if eco == 'maven':
                bucket_name = self.maven_model_bucket
                github_repo = self.maven_training_repo
            elif eco == 'pypi':
                bucket_name = self.pypi_model_bucket
                github_repo = self.pypi_training_repo
            elif eco == 'go':
                bucket_name = self.golang_model_bucket
                github_repo = self.golang_training_repo
            elif eco == 'npm':
                bucket_name = self.npm_model_bucket
                github_repo = self.npm_training_repo
            else:
                continue

            if bucket_name:
                logger.info('Storing user-input stacks for ecosystem {eco} at {dir}'.format(
                    eco=eco, dir=bucket_name + obj_key))
                try:
                    # Store the training content for each ecosystem
                    self.s3.store_json_content(content=training_data, bucket_name=bucket_name,
                                               obj_key=obj_key)
                    # Invoke the EMR API to kickstart retraining process
                    # This EMR invocation happens for all ecosystems almost at the same time.
                    # TODO - find an alternative if there is a need
                    self.invoke_emr_api(bucket_name, eco, model_version, github_repo)
                except Exception:
                    continue

    def normalize_worker_data(self, start_date, end_date, stack_data, worker, frequency='daily'):
        """Normalize worker data for reporting."""
        total_stack_requests = {'all': 0, 'npm': 0, 'maven': 0}
        if frequency == 'monthly':
            report_name = dt.strptime(end_date, '%Y-%m-%d').strftime('%Y-%m')
        else:
            report_name = dt.strptime(end_date, '%Y-%m-%d').strftime('%Y-%m-%d')

        stack_data = json.loads(stack_data)
        template = {
            'report': {
                'from': start_date,
                'to': end_date,
                'generated_on': dt.now().isoformat('T')
            },
            'stacks_summary': {},
            'stacks_details': []
        }
        all_deps = {'npm': [], 'maven': []}
        all_unknown_deps = {'npm': [], 'maven': []}
        all_unknown_lic = []
        all_cve_list = []

        total_response_time = {'all': 0.0, 'npm': 0.0, 'maven': 0.0}
        if worker == 'stack_aggregator_v2':
            stacks_list = {'npm': [], 'maven': []}
            for data in stack_data:
                stack_info_template = {
                    'ecosystem': '',
                    'stack': [],
                    'unknown_dependencies': [],
                    'license': {
                        'conflict': False,
                        'unknown': []
                    },
                    'security': {
                        'cve_list': [],
                    },
                    'response_time': ''
                }
                try:
                    user_stack_info = data[0]['stack_data'][0]['user_stack_info']
                    if len(user_stack_info['dependencies']) == 0:
                        continue

                    stack_info_template['ecosystem'] = user_stack_info['ecosystem']
                    total_stack_requests['all'] += 1
                    total_stack_requests[stack_info_template['ecosystem']] += 1

                    stack_info_template['stack'] = self.normalize_deps_list(
                        user_stack_info['dependencies'])
                    all_deps[user_stack_info['ecosystem']].append(stack_info_template['stack'])
                    stack_str = ','.join(stack_info_template['stack'])
                    stacks_list[user_stack_info['ecosystem']].append(stack_str)

                    unknown_dependencies = []
                    for dep in user_stack_info['unknown_dependencies']:
                        dep['package'] = dep.pop('name')
                        unknown_dependencies.append(dep)
                    stack_info_template['unknown_dependencies'] = self.normalize_deps_list(
                        unknown_dependencies)
                    all_unknown_deps[user_stack_info['ecosystem']].\
                        append(stack_info_template['unknown_dependencies'])

                    stack_info_template['license']['unknown'] = \
                        user_stack_info['license_analysis']['unknown_licenses']['really_unknown']
                    all_unknown_lic.append(stack_info_template['license']['unknown'])

                    for pkg in user_stack_info['analyzed_dependencies']:
                        for cve in pkg['security']:
                            stack_info_template['security']['cve_list'].append(cve)
                            all_cve_list.append('{cve}:{cvss}'.
                                                format(cve=cve['CVE'], cvss=cve['CVSS']))

                    ended_at, started_at = \
                        data[0]['_audit']['ended_at'], data[0]['_audit']['started_at']

                    response_time = self.datediff_in_millisecs(started_at, ended_at)
                    stack_info_template['response_time'] = '%f ms' % response_time
                    total_response_time['all'] += response_time
                    total_response_time[stack_info_template['ecosystem']] += response_time
                    template['stacks_details'].append(stack_info_template)
                except (IndexError, KeyError, TypeError) as e:
                    logger.exception('Error: %r' % e)
                    continue

            unique_stacks_with_recurrence_count = {
                'npm': self.populate_key_count(stacks_list['npm']),
                'maven': self.populate_key_count(stacks_list['maven'])
            }

            today = dt.today()
            # Invoke this every Monday. In Python, Monday is 0 and Sunday is 6
            if today.weekday() == 0:
                # Collate Data from Previous Month for Model Retraining
                collated_data = self.collate_raw_data(unique_stacks_with_recurrence_count,
                                                      'weekly')
                # Store ecosystem specific data to their respective Training Buckets
                self.store_training_data(collated_data)

            # Monthly data collection on the 1st of every month
            if today.date == 1:
                self.collate_raw_data(unique_stacks_with_recurrence_count, 'monthly')

            unique_stacks_with_deps_count =\
                self.set_unique_stack_deps_count(unique_stacks_with_recurrence_count)

            avg_response_time = {}
            if total_stack_requests['npm'] > 0:
                avg_response_time['npm'] = total_response_time['npm'] / total_stack_requests['npm']
            else:
                avg_response_time['npm'] = 0

            if total_stack_requests['maven'] > 0:
                avg_response_time['maven'] = \
                    total_response_time['maven'] / total_stack_requests['maven']
            else:
                avg_response_time['maven'] = 0

            # Get a list of unknown licenses
            unknown_licenses = []
            for lic_dict in self.flatten_list(all_unknown_lic):
                if 'license' in lic_dict:
                    unknown_licenses.append(lic_dict['license'])

            # generate aggregated data section
            template['stacks_summary'] = {
                'total_stack_requests_count': total_stack_requests['all'],
                'npm': {
                    'stack_requests_count': total_stack_requests['npm'],
                    'unique_dependencies_with_frequency':
                    self.populate_key_count(self.flatten_list(all_deps['npm'])),
                    'unique_unknown_dependencies_with_frequency':
                    self.populate_key_count(self.flatten_list(all_unknown_deps['npm'])),
                    'unique_stacks_with_frequency': unique_stacks_with_recurrence_count['npm'],
                    'unique_stacks_with_deps_count': unique_stacks_with_deps_count['npm'],
                    'average_response_time': '{} ms'.format(avg_response_time['npm'])
                },
                'maven': {
                    'stack_requests_count': total_stack_requests['maven'],
                    'total_stack_requests_count': total_stack_requests['maven'],
                    'unique_dependencies_with_frequency':
                        self.populate_key_count(self.flatten_list(all_deps['maven'])),
                    'unique_unknown_dependencies_with_frequency':
                        self.populate_key_count(self.flatten_list(all_unknown_deps['maven'])),
                    'unique_stacks_with_frequency': unique_stacks_with_recurrence_count['maven'],
                    'unique_stacks_with_deps_count': unique_stacks_with_deps_count['maven'],
                    'average_response_time': '{} ms'.format(avg_response_time['maven'])
                },
                'unique_unknown_licenses_with_frequency':
                    self.populate_key_count(unknown_licenses),
                'unique_cves':
                    self.populate_key_count(all_cve_list),
                'total_average_response_time':
                    '{} ms'.format(total_response_time['all'] / len(template['stacks_details'])),
            }
            try:
                obj_key = '{depl_prefix}/{freq}/{report_name}.json'.format(
                    depl_prefix=self.s3.deployment_prefix, freq=frequency, report_name=report_name
                )
                self.s3.store_json_content(content=template, obj_key=obj_key,
                                           bucket_name=self.s3.report_bucket_name)
            except Exception as e:
                logger.exception('Unable to store the report on S3. Reason: %r' % e)
            return template
        else:
            # todo: user feedback aggregation based on the recommendation task results
            return None

    def retrieve_worker_results(self, start_date, end_date, id_list=[], worker_list=[],
                                frequency='daily'):
        """Retrieve results for selected worker from RDB."""
        result = {}
        # convert the elements of the id_list to sql.Literal
        # so that the SQL query statement contains the IDs within quotes
        id_list = list(map(sql.Literal, id_list))
        ids = sql.SQL(', ').join(id_list).as_string(self.conn)

        for worker in worker_list:
            query = sql.SQL('SELECT {} FROM {} WHERE {} IN (%s) AND {} = \'%s\'').format(
                sql.Identifier('task_result'), sql.Identifier('worker_results'),
                sql.Identifier('external_request_id'), sql.Identifier('worker')
            )

            self.cursor.execute(query.as_string(self.conn) % (ids, worker))
            data = json.dumps(self.cursor.fetchall())

            # associate the retrieved data to the worker name
            result[worker] = self.normalize_worker_data(start_date, end_date, data, worker,
                                                        frequency)
        return result

    def retrieve_ingestion_results(self, start_date, end_date, frequency='daily'):
        """Retrieve results for selected worker from RDB."""
        result = {}

        # No of EPV failed ingesting into graph

        query = sql.SQL('SELECT EC.NAME, PK.NAME, VR.IDENTIFIER FROM ANALYSES AN,'
                        ' PACKAGES PK, VERSIONS VR, ECOSYSTEMS EC WHERE'
                        ' AN.STARTED_AT >= \'%s\' AND AN.STARTED_AT < \'%s\''
                        ' AND AN.VERSION_ID = VR.ID AND VR.PACKAGE_ID = PK.ID'
                        ' AND PK.ECOSYSTEM_ID = EC.ID AND VR.SYNCED2GRAPH = \'%s\'')

        self.cursor.execute(query.as_string(self.conn) % (start_date, end_date, 'FALSE'))
        data = json.dumps(self.cursor.fetchall())

        result['EPV_GRAPH_FAILED_DATA'] = data

        # No of EPV successfully ingesting into graph

        self.cursor.execute(query.as_string(self.conn) % (start_date, end_date, 'TRUE'))
        data = json.dumps(self.cursor.fetchall())

        result['EPV_GRAPH_SUCCESS_DATA'] = data

        self.normalize_ingestion_data(start_date, end_date, result, frequency)
        return result

    def normalize_ingestion_data(self, start_date, end_date, ingestion_data, frequency='daily'):
        """Normalize worker data for reporting."""
        report_type = 'ingestion-data'
        if frequency == 'monthly':
            report_name = dt.strptime(end_date, '%Y-%m-%d').strftime('%Y-%m')
        else:
            report_name = dt.strptime(end_date, '%Y-%m-%d').strftime('%Y-%m-%d')

        template = {
            'report': {
                'from': start_date,
                'to': end_date,
                'generated_on': dt.now().isoformat('T')
            },
            'ingestion_summary': {},
            'ingestion_details_v2': {}
        }

        all_deps_count = {'all': 0}
        failed_deps_count = {'all': 0}
        all_epv_list_v2 = {}

        # Graph Availability validation starts
        success_epv_data = ingestion_data['EPV_GRAPH_SUCCESS_DATA']
        success_epv_data = json.loads(success_epv_data)
        graph_input = []
        for data in success_epv_data:
            all_deps_count['all'] = all_deps_count['all'] + 1
            if all_deps_count.get(data[0]) is None:
                all_deps_count[data[0]] = 0
            all_deps_count[data[0]] = all_deps_count[data[0]] + 1
            graph_template = {
                'ecosystem': data[0],
                'name': data[1],
                'version': data[2]
            }
            graph_input.append(graph_template)

        # The below graph call determines the eistence of ingested epvs in the graph
        graph_output = generate_report_for_unknown_epvs(graph_input)
        for attributes, values in graph_output.items():
            versn_template = {}
            epv_arr = attributes.split('@')
            if all_epv_list_v2.get(epv_arr[0]) is None:
                all_epv_list_v2[epv_arr[0]] = {}
            all_epv_list_v2[epv_arr[0]][epv_arr[1]] = {}
            all_epv_list_v2[epv_arr[0]][epv_arr[1]]['package_known'] = values
            all_epv_list_v2[epv_arr[0]][epv_arr[1]]['versions'] = []
            versn_template['version'] = epv_arr[2]
            versn_template['ingested_in_graph'] = values
            if values == 'false':
                failed_deps_count['all'] = failed_deps_count['all'] + 1
                if failed_deps_count.get(epv_arr[0]) is None:
                    failed_deps_count[epv_arr[0]] = 0
                failed_deps_count[epv_arr[0]] = failed_deps_count[epv_arr[0]] + 1
            all_epv_list_v2[epv_arr[0]][epv_arr[1]]['versions'].append(versn_template)

        failed_epv_data = ingestion_data['EPV_GRAPH_FAILED_DATA']
        failed_epv_data = json.loads(failed_epv_data)
        for data in failed_epv_data:
            versn_template = {}
            all_deps_count['all'] = all_deps_count['all'] + 1
            if all_deps_count.get(data[0]) is None:
                all_deps_count[data[0]] = 0
            all_deps_count[data[0]] = all_deps_count[data[0]] + 1
            failed_deps_count['all'] = failed_deps_count['all'] + 1
            if failed_deps_count.get(data[0]) is None:
                failed_deps_count[data[0]] = 0
            failed_deps_count[data[0]] = failed_deps_count[data[0]] + 1
            if all_epv_list_v2.get(data[0]) is None:
                all_epv_list_v2[data[0]] = {}
            all_epv_list_v2[data[0]][data[1]] = {}
            all_epv_list_v2[data[0]][data[1]]['versions'] = []
            versn_template['version'] = data[2]
            versn_template['ingested_in_graph'] = 'false'
            all_epv_list_v2[data[0]][data[1]]['versions'].append(versn_template)
            graph_template = {
                'ecosystem': data[0],
                'name': data[1],
                'version': data[2]
            }
            graph_input.append(graph_template)

        # The below graph call determines the latest version information for
        # ingested epvs in the graph
        graph_output = generate_report_for_latest_version(graph_input)
        for attributes, values in graph_output.items():
            epv_arr = attributes.split('@')
            if all_epv_list_v2.get(epv_arr[0]) is None:
                all_epv_list_v2[epv_arr[0]] = {}
            all_epv_list_v2[epv_arr[0]][epv_arr[1]]['known_latest_version'] = \
                values['known_latest_version']
            all_epv_list_v2[epv_arr[0]][epv_arr[1]]['actual_latest_version'] = \
                values['actual_latest_version']
            if values['known_latest_version'] == '':
                all_epv_list_v2[epv_arr[0]][epv_arr[1]]['package_known'] = 'false'

        template['ingestion_details_v2'] = all_epv_list_v2

        # creating the epv ingestion statistics info according to the ecosystems
        template['ingestion_summary']['total_epv_ingestion_count'] = all_deps_count['all']
        for data in all_deps_count:
            if failed_deps_count.get(data) is None:
                failed_deps_count[data] = 0
            stats_template = {
                'epv_ingestion_count': all_deps_count[data],
                'epv_successfully_ingested_count':
                    all_deps_count[data] - failed_deps_count[data],
                'failed_epv_ingestion_count': failed_deps_count[data]
            }
            template['ingestion_summary'][data] = stats_template

        # Saving the final report in the relevant S3 bucket
        try:
            obj_key = '{depl_prefix}/{type}/epv/{report_name}.json'.format(
                depl_prefix=self.s3.deployment_prefix, type=report_type, report_name=report_name
            )
            self.s3.store_json_content(content=template, obj_key=obj_key,
                                       bucket_name=self.s3.report_bucket_name)
        except Exception as e:
            logger.exception('Unable to store the report on S3. Reason: %r' % e)
        return template

    def get_report(self, start_date, end_date, frequency='daily'):
        """Generate the stacks report."""
        ids = self.retrieve_stack_analyses_ids(start_date, end_date)
        ingestion_results = False
        if frequency == 'daily':
            result = self.retrieve_ingestion_results(start_date, end_date)
            epv_failed_data = result['EPV_GRAPH_FAILED_DATA']
            epv_failed_data = json.loads(epv_failed_data)
            epv_success_data = result['EPV_GRAPH_SUCCESS_DATA']
            epv_success_data = json.loads(epv_success_data)
            if len(epv_success_data) > 0 or len(epv_failed_data) > 0:
                ingestion_results = True
            else:
                ingestion_results = False
                logger.error('No ingestion data found from {s} to {e} to generate report'
                             .format(s=start_date, e=end_date))
        if len(ids) > 0:
            worker_result = self.retrieve_worker_results(
                start_date, end_date, ids, ['stack_aggregator_v2'], frequency)
            return worker_result, ingestion_results
        else:
            logger.error('No stack analyses found from {s} to {e} to generate an aggregated report'
                         .format(s=start_date, e=end_date))
            return False, ingestion_results
