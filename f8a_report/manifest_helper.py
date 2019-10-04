"""Dynamic Generation of Manifest files."""

import random
import json
from s3_helper import S3Helper
from template import pom_temp
from xml.etree import ElementTree as et
from io import StringIO
import logging
import os
import re

logger = logging.getLogger(__file__)
logging.basicConfig(level=logging.INFO)


class GetReport:
    """This creates a manifest file for all ecosystem and save to s3."""

    def __init__(self):
        """Init method for the Report helper class."""
        logger.info('Get Report Initialised')
        self.s3 = S3Helper()
        self.curr_dir = os.path.join(
            os.path.abspath(os.curdir), "f8a_report", "manifests")

    def generate_manifest_for_pypi(self, stack_report):
        """Generate manifest file for pypi."""
        logger.info('Generating Manifest for Pypi executed')
        file_name = "pylist.json"
        file_path = os.path.join(self.curr_dir, file_name)
        with open(file_path, 'w') as manifest:
            json.dump(stack_report, manifest)
        return self.save_manifest_to_s3(file_path=file_path, file_name=file_name)

    def generate_manifest_for_npm(self, stack_report):
        """Generate manifest file for npm."""
        logger.info('Generating manifest for NPM executed')
        file_name = "npmlist.json"
        file_path = os.path.join(self.curr_dir, file_name)
        with open(file_path, 'w') as manifest:
            json.dump(stack_report, manifest)
        return self.save_manifest_to_s3(file_path=file_path, file_name=file_name)

    def generate_manifest_for_maven(self, stack_report):
        """Generate manifest file for maven."""
        logger.info('Generate Manifest for Maven executed')
        file_name = "dependencies.txt"
        file_path = os.path.join(self.curr_dir, file_name)
        with open(file_path, 'w') as manifest:
            manifest.write(stack_report)
        return self.save_manifest_to_s3(file_path=file_path, file_name=file_name)

    def save_manifest_to_s3(self, file_path, file_name):
        """Save Generated manifest file to S3."""
        logger.info('Saving New Manifest in S3 executed')
        manifest_file_key = f'dynamic_manifests/{file_name}'
        self.s3.store_file_object(file_path=file_path,
                                  bucket_name=self.s3.report_bucket_name,
                                  file_name=manifest_file_key)


class FilterStacks:
    """This filters a Manifest file from collated stack report."""

    def filter_stacks_on_ecosystem(self, stack_report, stack_size):
        """Filter Stack Report on ecosystem."""
        logger.info('Filtering Stacks on ecosystem executed')
        npm_stack_data = []
        pypi_stack_data = []
        maven_stack_data = []
        for stack in stack_report:
            data = stack[0]['manifest'][0]

            if data['ecosystem'] == 'npm':
                npm_stack_data.append(data)
                continue

            if data['ecosystem'] == 'pypi':
                pypi_stack_data.append(data)
                continue

            if data['ecosystem'] == 'maven':
                maven_stack_data.append(data)
                continue

        if npm_stack_data:
            npm_stack_data = self.filter_stacks_on_size(npm_stack_data, stack_size)
            npm_stack_data = self.clean_stacks(npm_stack_data)
            GetReport().generate_manifest_for_npm(npm_stack_data[0])
        if maven_stack_data:
            maven_stack_data = self.filter_stacks_on_size(maven_stack_data, stack_size)
            GetReport().generate_manifest_for_maven(maven_stack_data[0]['content'])
        if pypi_stack_data:
            pypi_stack_data = self.filter_stacks_on_size(pypi_stack_data, stack_size)
            pypi_stack_data = self.clean_stacks(pypi_stack_data)
            GetReport().generate_manifest_for_pypi(pypi_stack_data[0])

    def filter_stacks_on_size(self, stack_report, stack_size):
        """Filter Stack Report on size and convert into dict."""
        logger.info('Filtering Stacks on size Executed')
        try:
            sampled_stack_report = random.sample(stack_report, stack_size)
        except ValueError:
            # stack size is smaller than stack length
            sampled_stack_report = random.sample(stack_report, len(stack_report))
        return sampled_stack_report

    def clean_stacks(self, sampled_stack_reports):
        """Remove Spaces and Tabs from Json Data."""
        return [json.loads(re.sub(r'\s+', ' ', stack_report['content']))
                for stack_report in sampled_stack_reports]


def manifest_interface(stack_report, stack_size):
    """Initialize function, executed first."""
    logger.info('Manifest Generation Executed')
    FilterStacks().filter_stacks_on_ecosystem(
        stack_report=stack_report, stack_size=stack_size)
    return


if __name__ == '__main__':
    with open("f8a_report/manifests.json") as myfile:
        file_content = json.load(myfile)
    FilterStacks().filter_stacks_on_ecosystem(stack_report=file_content, stack_size=2)
