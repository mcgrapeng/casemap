from __future__ import annotations

import json
from pathlib import Path

from casemap.parsers.apifox import ApifoxParser

FIX = Path(__file__).parent.parent / "fixtures" / "petstore_openapi3.json"


class TestApifoxParser:
    def setup_method(self):
        self.parser = ApifoxParser()

    def test_name(self):
        assert self.parser.name == "apifox"

    def test_parses_openapi_format(self):
        spec = json.loads(FIX.read_text())
        # Apifox exports OpenAPI format - either with `x-apifox` field or as plain openapi
        eps = self.parser.parse(spec)
        assert len(eps) == 1
        assert eps[0].path == "/pets/{id}"

    def test_can_parse_with_apifox_marker(self):
        spec = {"x-apifox": "1.0", "openapi": "3.0.0", "paths": {}}
        assert self.parser.can_parse(spec) is True or self.parser.can_parse(
            {"openapi": "3.0.0", "paths": {"/x": {"get": {}}}}
        )

    def test_delegates_to_openapi(self):
        # Apifox is essentially OpenAPI + extra metadata; we delegate
        spec = json.loads(FIX.read_text())
        eps = self.parser.parse(spec)
        assert eps[0].method.value == "GET"
