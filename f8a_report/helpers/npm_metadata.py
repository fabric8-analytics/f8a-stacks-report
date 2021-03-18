# Copyright © 2020 Red Hat Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Author: Dharmendra G Patel <dhpatel@redhat.com>
#
"""Class to update NPM package details."""
import datetime
import requests
import logging
from helpers.s3_helper import S3Helper

logger = logging.getLogger(__file__)

NPM_PACKAGE_FILE_PATH = "training-utils/node-package-details.json"


class NPMMetadata:
    """NPM metadata fetcher."""

    def __init__(self, s3Helper=S3Helper, github_token=str,
                 bucket_name=str, manifest_data=dict()):
        """Set obect default memebers."""
        self.s3Helper = s3Helper
        self.github_token = github_token
        self.bucket_name = bucket_name
        self.package_list = self._flatten_list(manifest_data)
        self.existing_data = self._load_data()

        self.stats = {
            'existing_count': len(self.existing_data),
            'unique_manifest_count': len(self.package_list),
            'metadata_exists': 0,
            'total_missing': 0,
            'new_packages': 0,
            'updated_count': 0,
            'still_missing': 0,
            'fetched_from_npm': 0,
            'fetched_from_github': 0,
            'npm_fetch_errors': 0,
            'github_fetch_errors': 0,
        }

    def update(self):
        """Read and update metadata for all NPM packages in S3."""
        logger.debug("Existing node package length: %d", self.stats['existing_count'])
        logger.debug("Number of node package in manifest: %d", self.stats['unique_manifest_count'])

        index = 0
        # Force update package after 30 days (2592000 seconds) to get latest version data.
        update_timestamp = int(datetime.datetime.now().timestamp()) - 2592000
        for package_name in self.package_list:
            # Print progress for every 500 packages
            if index % 500 == 0:
                logger.debug("Processing [%d/%d %d%%] ==> '%s'", index + 1,
                             self.stats['unique_manifest_count'],
                             index * 100 / self.stats['unique_manifest_count'], package_name)
            index += 1
            package_details = self.existing_data.get(package_name, None)

            if not package_details or \
               package_details.get("updated_timestamp", 0) < update_timestamp:
                self.stats['total_missing'] += 1

                if not package_details:
                    self.stats['new_packages'] += 1

                new_package_details = self._fetch(package_name)
                if new_package_details:
                    logger.info("Updated package '%s' has keywords %s",
                                new_package_details['name'],
                                new_package_details['keywords'])
                    self.stats['updated_count'] += 1
                    self.existing_data[package_name] = new_package_details
                else:
                    self.stats['still_missing'] += 1
            else:
                self.stats['metadata_exists'] += 1

        logger.info("Processing completed [%d/%d %d%%]", index,
                    self.stats['unique_manifest_count'],
                    index * 100 / self.stats['unique_manifest_count'])

        self._save_data()
        self._print_stats()

    def _print_stats(self):
        """Print statistics about operation."""
        logger.debug("NPM Metadata update statistics")
        logger.debug("    1. Existing number of NPM packages : %d", self.stats['existing_count'])
        logger.debug("    2. Unique packages in manifest : %d", self.stats['unique_manifest_count'])
        logger.debug("    3. Packages with metadata : %d", self.stats['metadata_exists'])
        logger.debug("    4. Total missing packages : %d", self.stats['total_missing'])
        logger.debug("    5. New packages : %d", self.stats['new_packages'])
        logger.debug("    6. Packages updated : %d", self.stats['updated_count'])
        logger.debug("    7. Packages missing after update : %d", self.stats['still_missing'])
        logger.debug("    8. Data fetched from registry : %d", self.stats['fetched_from_npm'])
        logger.debug("    9. Registry fetch errors : %d", self.stats['npm_fetch_errors'])
        logger.debug("   10. Data fetched from github : %d", self.stats['fetched_from_github'])
        logger.debig("   11. Github fetch errors : %d", self.stats['github_fetch_errors'])

    def _fetch(self, package_name=str):
        """Fetch metadata for a package and return it as json."""
        package_metadata = self._from_npm_registry(package_name)

        # If key words are not found in repository, get it from github.
        if package_metadata and len(package_metadata.get("keywords", [])) == 0 and \
           len(package_metadata.get("repositoryurl", "")) > 0:
            logger.info("Trying to fetch keywords from Github for '%s'", package_name)

            package_metadata["keywords"] = self._from_github(package_metadata["repositoryurl"])

        return package_metadata

    def _flatten_list(self, manifest_data):
        """Create a flatten list for given list of list."""
        package_dict = manifest_data.get("package_dict", {})
        package_list = package_dict.get("user_input_stack", []) + \
            package_dict.get("bigquery_data", [])
        flatten_package_list = [m for sub_list in package_list for m in sub_list if len(m) > 0]
        unique_flatten_package_list = list(set(flatten_package_list))
        logger.info("Found total %d packages and unque %d packages in manifest file",
                    len(package_list), len(unique_flatten_package_list))
        return unique_flatten_package_list

    def _load_data(self):
        """Load the node registry dump from S3 bucket and tranform into dict for quick access."""
        return self.s3Helper.read_json_object(bucket_name=self.bucket_name,
                                              obj_key=NPM_PACKAGE_FILE_PATH) or {}

    def _save_data(self):
        """Get back data into original format and save it to a file."""
        self.s3Helper.store_json_content(
            content=self.existing_data, bucket_name=self.bucket_name,
            obj_key=NPM_PACKAGE_FILE_PATH)

    def _get_org_package_name(self, repo_url):
        """Give the Query Parameters which are organization and package name respectively."""
        org = ""
        package_name = ""
        try:
            url_chunks = (repo_url.rsplit('/', 2))
            if 'github' not in url_chunks[1]:
                org = url_chunks[1]
            package_name = url_chunks[2]
            return org, package_name
        except Exception as e:
            logger.error("Could not as org and package name for repo %s, it throws error %s",
                         repo_url, e)

        return org, package_name

    def _github_clean_response(self, response_json):
        """Clean the api response json."""
        topic_edges = response_json["data"]["organization"]["repository"]["repositoryTopics"]
        topic_names = [i.get("node", {}).get("topic", {}).get("name", None)
                       for i in topic_edges["edges"]]
        topic_names = [i for i in topic_names if i is not None]
        return topic_names

    def _from_github(self, repo_url=str):
        """Find the keywords from the Github Graph QL."""
        github_org, package_name = self._get_org_package_name(repo_url)
        api_url = "https://api.github.com/graphql"
        payload = {
            "query": "query{organization(login:\"" + github_org + "\")"
                     "{name url repository(name:\"" + package_name + "\")"
                     "{name url description repositoryTopics(first: 10)"
                     "{edges {node{topic{name}}}}}}}"
        }
        headers = {"Authorization": "token %s" % self.github_token}
        try:
            response = requests.post(url=api_url, json=payload, headers=headers)
            keywords = list(self._github_clean_response(response.json()))
            self.stats['fetched_from_github'] += 1
            return keywords
        except Exception as e:
            self.stats['github_fetch_errors'] += 1
            logger.warning("Github token missing / response is not coming, it throws %s", e)

        return []

    def _from_npm_registry(self, package_name=str):
        """Find the keywords from NPM registry(through api)."""
        data_dict = None
        api_url = "https://registry.npmjs.org/" + str(package_name)
        try:
            response = requests.get(api_url)
            json_data = response.json()
            latest_version = json_data.get("dist-tags", {}).get("latest", None)
            if latest_version:
                latest_version_data = json_data.get("versions", {}).get(latest_version, {})
                data_dict = {
                    "name": json_data.get("name", ""),
                    "description": json_data.get("description", ""),
                    "version": latest_version,
                    "keywords": latest_version_data.get("keywords", []),
                    "dependencies":
                        list(latest_version_data.get("dependencies", {}).keys()),
                    "homepage": json_data.get("homepage", ""),
                    "repositoryurl": json_data.get("repository", {}).get("url", ""),
                    "updated_timestamp": int(datetime.datetime.now().timestamp()),
                }
                # Other fields that were present in past, but not used for training model are
                # below. Removing this fields saves lot of space while storing pacakge data in
                # S3.
                #  "devDependencies":
                #        list(latest_version_data.get("devDependencies", {}).keys()),
                #  "peerDependencies":
                #        list(latest_version_data.get("peerDependencies", {}).keys()),
                #  "readme": json_data.get("readme", ""),

                self.stats['fetched_from_npm'] += 1
        except Exception as e:
            self.stats['npm_fetch_errors'] += 1
            logger.error("Can't fetch the keywords for %s from NPM Registry, it throws %s",
                         package_name, e)

        return data_dict
