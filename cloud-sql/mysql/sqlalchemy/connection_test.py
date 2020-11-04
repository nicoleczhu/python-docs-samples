from contextlib import contextmanager
import logging
import os
from typing import Dict

import pymysql
import pytest

import main


logger = logging.getLogger()


@pytest.mark.usefixtures('tcp_db_connection')
def test_tcp_connection(tcp_db_connection):
    assert tcp_db_connection is not None


@pytest.mark.usefixtures('unix_db_connection')
def test_unix_connection(unix_db_connection):
    assert unix_db_connection is not None


@pytest.mark.usefixtures('tcp_db_connection')
def test_get(tcp_db_connection):
    main.create_tables()
    context = main.get_index_context()
    assert isinstance(context, dict)
    assert len(context.get('recent_votes')) >= 0
    assert context.get('tab_count') >= 0
    assert context.get('space_count') >= 0


env_map = {
    'MYSQL_USER': 'DB_USER',
    'MYSQL_PASSWORD': 'DB_PASS',
    'MYSQL_DATABASE': 'DB_NAME',
    'MYSQL_INSTANCE': 'CLOUD_SQL_CONNECTION_NAME',
}


@pytest.fixture
def tcp_db_connection():
    tcp_env_map = {key: value for key, value in env_map.items()}
    tcp_env_map['MYSQL_HOST'] = 'DB_HOST'

    with mapped_env_variables(tcp_env_map):
        yield from _common_setup()


@pytest.fixture
def unix_db_connection():
    with mapped_env_variables(env_map):
        yield from _common_setup()


def _common_setup():
    try:
        pool = main.init_connection_engine()
    except pymysql.err.OperationalError as e:
        logger.warning(
            'Could not connect to the production database. '
            'If running tests locally, is the cloud_sql_proxy currently running?'
        )
        raise e

    with pool.connect() as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS test_table "
            "( vote_id SERIAL NOT NULL, time_cast timestamp NOT NULL, "
            "candidate CHAR(6) NOT NULL, PRIMARY KEY (vote_id) );"
        )

    yield pool

    with pool.connect() as conn:
        conn.execute("DROP TABLE IF EXISTS test_table")


@contextmanager
def mapped_env_variables(env_map: Dict):
    """Copies values in the environment to other values, also in
    the environment.

    In `env_map`, keys are source environment variables and values
    are destination environment variables.
    """
    for key, value in env_map.items():
        os.environ[value] = os.environ[key]

    try:
        yield
    finally:
        for variable_name in env_map.values():
            if os.environ.get(variable_name):
                del os.environ[variable_name]
