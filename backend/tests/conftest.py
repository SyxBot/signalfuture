import json
import os

import pytest


FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


def load_fixture(name: str) -> dict:
    with open(os.path.join(FIXTURES_DIR, name)) as f:
        return json.load(f)


@pytest.fixture
def rank_response():
    return load_fixture("rank_response.json")


@pytest.fixture
def security_response():
    return load_fixture("security_response.json")


@pytest.fixture
def wallet_response():
    return load_fixture("wallet_response.json")


@pytest.fixture
def raw_token(rank_response):
    return rank_response["data"]["rank"][0]
