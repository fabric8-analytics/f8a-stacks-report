"""Dynamic Generation of Manifest files."""

import random
import json
from s3_helper import S3Helper
from template import pom_temp
from xml.etree import ElementTree as et
from io import StringIO
import logging
import os


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
        data = []
        for package_name, version in stack_report:
            data.append({"package": package_name,
                         "version": version,
                         "deps": []})

        with open(file_path, 'w') as manifest:
            json.dump(data, manifest)
        return self.save_manifest_to_s3(file_path=file_path, file_name=file_name)

    def generate_manifest_for_npm(self, stack_report):
        """Generate manifest file for npm."""
        logger.info('Generating manifest for NPM executed')
        file_name = "package.json"
        file_path = os.path.join(self.curr_dir, file_name)
        data = {"dependencies": {f"{dependency[0]}": f"{dependency[1]}"
                                 for dependency in stack_report}}
        with open(file_path, 'w') as manifest:
            json.dump(data, manifest)
        return self.save_manifest_to_s3(file_path=file_path, file_name=file_name)

    def generate_manifest_for_maven(self, stack_report):
        """Generate manifest file for maven."""
        logger.info('Generate Manifest for Maven executed')
        file_name = "pom.xml"
        file_path = os.path.join(self.curr_dir, file_name)
        tree = et.ElementTree(self.remove_namespace())
        dependencies = tree.find("dependencies")
        for dep in stack_report:
            group_id, artifact_id = dep[0].split(":")
            dependency = self.sub_element_with_text(dependencies, 'dependency')
            self.sub_element_with_text(dependency, 'groupId', text=group_id)
            self.sub_element_with_text(dependency, 'artifactId', text=artifact_id)
            self.sub_element_with_text(dependency, 'version', text=dep[1])
        self.indent(tree.getroot())
        with open(file_path, 'w', encoding='utf-8') as manifest:
            tree.write(manifest, encoding='unicode', xml_declaration=True)
        return self.save_manifest_to_s3(file_path=file_path, file_name=file_name)

    def indent(self, elem, level=4):
        """Prettify xml."""
        i = "\n" + level * "  "
        if len(elem):
            if not elem.text or not elem.text.strip():
                elem.text = i + "  "
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
            for elem in elem:
                self.indent(elem, level + 1)
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
        else:
            if level and (not elem.tail or not elem.tail.strip()):
                elem.tail = i

    def save_manifest_to_s3(self, file_path, file_name):
        """Save Generated manifest file to S3."""
        logger.info('Saving New Manifest in S3 executed')
        manifest_file_key = f'dynamic_manifests/{file_name}'
        self.s3.store_file_object(file_path=file_path,
                                  bucket_name=self.s3.report_bucket_name,
                                  file_name=manifest_file_key)

    @staticmethod
    def remove_namespace():
        """Remove default namespace added by fromstring method."""
        logger.info('Namespace removal executed')
        it = et.iterparse(StringIO(pom_temp))
        for _, el in it:
            if '}' in el.tag:
                el.tag = el.tag.split('}', 1)[1]  # strip all namespaces
        return it.root

    @staticmethod
    def sub_element_with_text(parent, tag, text=None):
        """Adding new Element in nest to parent."""
        attrib = {}
        element = parent.makeelement(tag, attrib)
        parent.append(element)
        element.text = text
        return element


class FilterStacks:
    """This filters a Manifest file from collated stack report."""

    def filter_stacks_on_ecosystem(self, stack_report, stack_size=1):
        """Filter Stack Report on ecosystem."""
        logger.info('Filtering Stacks on ecosystem executed')
        if stack_report['pypi']:
            pypi_stack_data = stack_report['pypi']['user_input_stack']
            pypi_stack_data = self.filter_stacks_on_size(pypi_stack_data, stack_size)
            GetReport().generate_manifest_for_pypi(pypi_stack_data)

        if stack_report['npm']:
            npm_stack_data = stack_report['npm']['user_input_stack']
            npm_stack_data = self.filter_stacks_on_size(npm_stack_data, stack_size)
            GetReport().generate_manifest_for_npm(npm_stack_data)

        if stack_report['maven']:
            maven_stack_data = stack_report['maven']['user_input_stack']
            maven_stack_data = self.filter_stacks_on_size(maven_stack_data, stack_size)
            GetReport().generate_manifest_for_maven(maven_stack_data)

    @staticmethod
    def filter_stacks_on_size(stack_report, stack_size):
        """Filter Stack Report on size."""
        logger.info('Filtering Stacks on size Executed')
        try:
            sampled_stack_report = random.sample(stack_report.keys(), stack_size)
        except ValueError:
            # stack size is smaller than stack length
            stack_report = random.sample(stack_report, len(stack_report))
        # selecting random only keys
        stack_report = list(filter(lambda x: x in sampled_stack_report, stack_report))[0]
        # Parsing over each Dependency and Splitting over space and ,
        return list(map(lambda x: x.split(), stack_report.split(',')))


def manifest_interface(stack_report, stack_size):
    """Initialize function, executed first."""
    logger.info('Manifest Generation Executed')
    FilterStacks().filter_stacks_on_ecosystem(
        stack_report=stack_report, stack_size=stack_size)


if __name__ == '__main__':
    with open("f8a_report/collated-weekly.json") as myfile:
        file_content = json.load(myfile)
    FilterStacks().filter_stacks_on_ecosystem(stack_report=file_content, stack_size=1)
