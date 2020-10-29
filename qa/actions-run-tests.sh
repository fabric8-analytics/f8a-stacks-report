#!/bin/bash

COVERAGE_THRESHOLD=60
printf "%sShutting down docker-compose ..." "${NORMAL}"


gc() {
  retval=$?
  docker-compose -f ${SCRIPT_DIR}/../docker-compose.yml down -v || :
  rm -rf venv/
  exit $retval
}

trap gc EXIT SIGINT

function start_postgres {
    #pushd local-setup/
    echo "Invoke Docker Compose services"
    docker-compose -f docker-compose.yml up  -d
    #popd
}

start_postgres
PYTHONPATH=$(pwd)/f8a_report/
export PYTHONPATH
export GENERATE_MANIFESTS="True"

export POSTGRESQL_USER='coreapi'
export POSTGRESQL_PASSWORD='coreapipostgres'
export POSTGRESQL_DATABASE='coreapi'
export PGBOUNCER_SERVICE_HOST='0.0.0.0'
export PGPORT="5432"
export REPORT_BUCKET_NAME="not-set"
export MANIFESTS_BUCKET="not-set"
export AWS_S3_ACCESS_KEY_ID="not-set"
export AWS_S3_SECRET_ACCESS_KEY="not-set"
export AWS_S3_REGION="not-set"

pip install -U pip;
pip install virtualenv;
virtualenv --version;
virtualenv -p python3 venv && source venv/bin/activate;
pip install -r requirements.txt
pip install -r tests/requirements.txt
pip install git+https://github.com/fabric8-analytics/fabric8-analytics-utils.git@${F8A_UTIL_VERSION}
pip install git+https://git@github.com/fabric8-analytics/fabric8-analytics-version-comparator.git#egg=f8a_version_comparator
pip install "$(pwd)/."

python "$(which pytest)" -s --cov=f8a_report/ --cov-report=xml --cov-fail-under=$COVERAGE_THRESHOLD -vv tests
echo "------------------ CI Passed ------------------ "
echo "----------------------------------------------- "
