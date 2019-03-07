from .report_helper import Postgres

from psycopg2 import sql


class Report:
    """Generic report that handles a dictionary and can store it to S3."""

    def __init__(self):
        self.report_dictionary = dict()
        self.name = None  # TODO:
        # TODO: include the S3 helper?

    def store_to_s3(self):
        pass


class EPVReport:

    def __init__(self):
        """Create an empty report."""
        self.rds = Postgres()  # TODO: error handling? There is no in the class

    def get_list_of_scheduled_ingestions(self):
        """Connect to RDS and get a list of scheduled ingestions."""
        QUERY = r"SELECT EC.NAME, PK.NAME, VR.IDENTIFIER " \
                r"FROM ANALYSES AN, PACKAGES PK, ECOSYSTEMS EC " \
                r"WHERE AN.STARTED_AT >= '{}' AND " \
                r"WHERE AN.STARTED_AT < '{}' AND " \
                r"AN.VERSION_ID = VR.ID AND VR.PACKAGE_ID = PK.ID AND PK.ECOSYSTEM_ID = EC.ID"
        query = sql.SQL(QUERY).format(
            sql.Literal("2018-12-21"), sql.Literal("2018-12-25")
        )

    def get_list_of_failed_ingestions(self):
        """Connect to RDS and get a list of failed ingestions."""

    def get_list_of_successful_ingestions(self):
        """Connect to RDS and get a list of successful ingestions."""

    def get_list_of_executed_workers(self):
        """Connect to RDS and get a list of executed workers and their exit codes."""
