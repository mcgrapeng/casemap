from __future__ import annotations

import json
from pathlib import Path

import pytest

from casemap.models.endpoint import HttpMethod
from casemap.parsers.openapi import OpenAPIParser

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def swagger_spec():
    return json.loads((FIXTURE_DIR / "petstore_swagger.json").read_text())


@pytest.fixture
def openapi3_spec():
    return json.loads((FIXTURE_DIR / "petstore_openapi3.json").read_text())


class TestOpenAPIParser:
    def setup_method(self):
        self.parser = OpenAPIParser()

    def test_name_and_version(self):
        assert self.parser.name == "openapi"
        assert self.parser.version  # non-empty

    def test_can_parse_swagger2(self, swagger_spec):
        assert self.parser.can_parse(swagger_spec) is True

    def test_can_parse_openapi3(self, openapi3_spec):
        assert self.parser.can_parse(openapi3_spec) is True

    def test_can_parse_invalid(self):
        assert self.parser.can_parse({"random": "object"}) is False
        assert self.parser.can_parse("not a dict") is False

    def test_parse_swagger2_yields_endpoints(self, swagger_spec):
        eps = self.parser.parse(swagger_spec)
        # 4 ops: GET /pets, POST /pets, GET /pets/{id}, DELETE /pets/{id}
        assert len(eps) == 4
        paths = {(e.method, e.path) for e in eps}
        assert (HttpMethod.GET, "/pets") in paths
        assert (HttpMethod.POST, "/pets") in paths
        assert (HttpMethod.GET, "/pets/{id}") in paths
        assert (HttpMethod.DELETE, "/pets/{id}") in paths

    def test_parse_openapi3(self, openapi3_spec):
        eps = self.parser.parse(openapi3_spec)
        assert len(eps) == 1
        ep = eps[0]
        assert ep.path == "/pets/{id}"
        assert ep.method == HttpMethod.GET
        assert len(ep.parameters) == 1
        assert ep.parameters[0].name == "id"

    def test_parameters_have_constraints(self, swagger_spec):
        eps = self.parser.parse(swagger_spec)
        list_pets = next(e for e in eps if e.method == HttpMethod.GET and e.path == "/pets")
        limit_param = next(p for p in list_pets.parameters if p.name == "limit")
        assert limit_param.constraints.get("minimum") == 1
        assert limit_param.constraints.get("maximum") == 100

    def test_tags_preserved(self, swagger_spec):
        eps = self.parser.parse(swagger_spec)
        assert all(e.tags == ["pets"] for e in eps)

    def test_responses_extracted(self, swagger_spec):
        eps = self.parser.parse(swagger_spec)
        get_pet = next(e for e in eps if e.method == HttpMethod.GET and e.path == "/pets/{id}")
        codes = {r.status_code for r in get_pet.responses}
        assert codes == {"200", "404"}

    def test_invalid_input_raises(self):
        from casemap._internal.exceptions import ParseError

        with pytest.raises(ParseError):
            self.parser.parse({"swagger": "2.0", "paths": "not a dict"})
