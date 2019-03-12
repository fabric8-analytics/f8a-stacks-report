from enum import Enum

from .report_helper import Postgres

from psycopg2 import sql


class ReportType(Enum):
    DAILY = 1,
    WEEKLY = 2,
    MONTHLY = 3,


class Report:
    """Generic report that handles a dictionary and can store it to S3."""

    def __init__(self):
        self.report_data = dict()
        self.report_directory = None
        self.name = None  # TODO:
        # TODO: include the S3 helper?

    def store_to_s3(self):
        pass


class EPVReport(Report):

    def __init__(self):
        """Create an empty report."""
        super(EPVReport, self).__init__()
        self.pg = Postgres()  # TODO: error handling? There is no in the class

    def generate_report(self, report_type):
        """Generate a report for the previous day/week/month.

        This method can fail in various ways, because it communicates with RDS and S3. Make sure
        to handle exceptions.
        """
        from_date = None
        till_date = None
        self.report_directory = None
        # TODO: ^^^--- fill in the data and call the functions ---vvv

    @staticmethod
    def epv_tuple_into_dict(epv):
        return {
            'ecosystem': epv[0],
            'package': epv[1],
            'version': epv[2]
        }

    def get_list_of_scheduled_ingestions(self):
        """Connect to RDS and get a list of scheduled ingestions."""
        # source: http://initd.org/psycopg/docs/usage.html#passing-parameters-to-sql-queries
        # SELECT ECOSYSTEMS.NAME, PACKAGES.NAME, VERSIONS.IDENTIFIER
        # FROM ANALYSES
        # WHERE ANALYSES.STARTED_AT BETWEEN %s and %s
        # INNER JOIN VERSIONS ON ANALYSES.VERSION_ID=VERSIONS.ID
        # INNER JOIN PACKAGES ON ANALYSES.PACKAGE_ID=PACKAGES.ID
        # INNER JOIN ECOSYSTEMS ON PACKAGES.ECOSYSTEM_ID=ECOSYSTEM.ID
        self.pg.cursor.execute("""
                               SELECT EC.NAME, PK.NAME, VR.IDENTIFIER
                               FROM ANALYSES AN, PACKAGES PK, VERSIONS VR, ECOSYSTEMS EC
                               WHERE AN.STARTED_AT >= %s
                               AND WHERE AN.STARTED_AT < %s
                               AND AN.VERSION_ID = VR.ID
                               AND VR.PACKAGE_ID = PK.ID
                               AND PK.ECOSYSTEM_ID = EC.ID
                               """,
                               ("2018-12-21", "2018-12-25"))
        raw_data = self.pg.cursor.fetchall()
        return list(map(EPVReport.epv_tuple_into_dict, raw_data))

    def get_list_of_failed_ingestions(self):
        """Connect to RDS and get a list of failed ingestions."""

    def get_list_of_successful_ingestions(self):
        """Connect to RDS and get a list of successful ingestions."""

    def get_list_of_executed_workers(self):
        """Connect to RDS and get a list of executed workers and their exit codes."""
