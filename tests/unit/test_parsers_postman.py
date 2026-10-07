from __future__ import annotations

import json
from pathlib import Path

import pytest

from casemap.models.endpoint import HttpMethod
from casemap.parsers.postman import PostmanParser

FIX = Path(__file__).parent.parent / "fixtures" / "postman_collection.json"


@pytest.fixture
def collection():
    return json.loads(FIX.read_text())


class TestPostmanParser:
    def setup_method(self):
        self.parser = PostmanParser()

    def test_name(self):
        assert self.parser.name == "postman"

    def test_can_parse(self, collection):
        assert self.parser.can_parse(collection) is True

    def test_cannot_parse_other(self):
        assert self.parser.can_parse({"openapi": "3.0.0"}) is False

    def test_parse_flat(self, collection):
        eps = self.parser.parse(collection)
        # 3 endpoints: List users, Create user, Get user (nested counted too)
        assert len(eps) == 3
        methods_paths = {(e.method, e.path) for e in eps}
        assert (HttpMethod.GET, "/users") in methods_paths
        assert (HttpMethod.POST, "/users") in methods_paths
        assert (HttpMethod.GET, "/users/1") in methods_paths

    def test_query_params(self, collection):
        eps = self.parser.parse(collection)
        list_users = next(e for e in eps if e.method == HttpMethod.GET and e.path == "/users")
        param_names = {p.name for p in list_users.parameters}
        assert "limit" in param_names

    def test_body(self, collection):
        eps = self.parser.parse(collection)
        create = next(e for e in eps if e.method == HttpMethod.POST and e.path == "/users")
        assert create.request_body is not None
        assert create.request_body.location == "body"

    def test_summary_from_name(self, collection):
        eps = self.parser.parse(collection)
        summaries = {e.summary for e in eps}
        assert "List users" in summaries
        assert "Create user" in summaries
