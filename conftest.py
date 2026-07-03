"""
Root conftest for Spotter AI test suite.

Provides shared fixtures across all test modules.
"""

import pytest


@pytest.fixture(autouse=True)
def _enable_db_access_for_all_tests(db: None) -> None:
    """
    Automatically grant database access to every test.

    The ``db`` fixture is a pytest-django built-in that enables
    database access. By using ``autouse=True`` we avoid having to
    mark every single test with ``@pytest.mark.django_db``.
    """
