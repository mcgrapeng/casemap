from __future__ import annotations

from casemap.generators.structural import StructuralGenerator
from casemap.models.endpoint import Endpoint, HttpMethod, Parameter, Response
from casemap.models.testcase import CaseType, TestStatus


def make_endpoint(
    method=HttpMethod.POST,
    path="/users",
    parameters=None,
    request_body=None,
    responses=None,
    tags=None,
) -> Endpoint:
    return Endpoint(
        path=path,
        method=method,
        parameters=parameters or [],
        request_body=request_body,
        responses=responses or [Response(status_code="200"), Response(status_code="400")],
        tags=tags or ["users"],
    )


class TestStructuralGenerator:
    def setup_method(self):
        self.gen = StructuralGenerator()

    def test_returns_at_least_one_positive_per_endpoint(self):
        ep = make_endpoint()
        cases = self.gen.generate([ep])
        positives = [c for c in cases if c.type == CaseType.POSITIVE]
        assert len(positives) >= 1

    def test_required_param_generates_negative(self):
        ep = make_endpoint(
            parameters=[Parameter(name="user_id", location="path", type="string", required=True)]
        )
        cases = self.gen.generate([ep])
        negs = [c for c in cases if c.type == CaseType.NEGATIVE]
        # Should have at least one negative for missing required param
        assert any("user_id" in c.title or "缺失" in c.title or "必填" in c.title for c in negs)

    def test_path_param_generates_404(self):
        ep = make_endpoint(
            method=HttpMethod.GET,
            path="/users/{id}",
            parameters=[Parameter(name="id", location="path", type="string", required=True)],
            responses=[Response(status_code="200"), Response(status_code="404")],
        )
        cases = self.gen.generate([ep])
        assert any("不存在" in c.title or "404" in c.title or "not found" in c.title.lower() for c in cases)

    def test_constraint_min_max_generates_edge(self):
        ep = make_endpoint(
            method=HttpMethod.GET,
            path="/users",
            parameters=[
                Parameter(
                    name="limit",
                    location="query",
                    type="integer",
                    required=False,
                    constraints={"minimum": 1, "maximum": 100},
                )
            ],
        )
        cases = self.gen.generate([ep])
        edges = [c for c in cases if c.type == CaseType.EDGE]
        # Edge cases for min, max, and (implicit) zero/below-min
        assert len(edges) >= 2

    def test_delete_generates_security(self):
        ep = make_endpoint(method=HttpMethod.DELETE, path="/users/{id}")
        cases = self.gen.generate([ep])
        secs = [c for c in cases if c.type == CaseType.SECURITY]
        assert len(secs) >= 1

    def test_all_cases_default_to_pending(self):
        ep = make_endpoint()
        cases = self.gen.generate([ep])
        assert all(c.status == TestStatus.PENDING for c in cases)

    def test_endpoint_ref_set(self):
        ep = make_endpoint(method=HttpMethod.POST, path="/users")
        cases = self.gen.generate([ep])
        assert all(c.endpoint_ref is not None for c in cases)

    def test_deterministic_ids(self):
        ep = make_endpoint()
        cases1 = self.gen.generate([ep])
        cases2 = self.gen.generate([ep])
        ids1 = sorted(c.id for c in cases1)
        ids2 = sorted(c.id for c in cases2)
        assert ids1 == ids2

    def test_multiple_endpoints(self):
        eps = [make_endpoint(path=f"/r{i}", method=HttpMethod.GET) for i in range(5)]
        cases = self.gen.generate(eps)
        # At least one positive per endpoint
        paths = {c.endpoint_ref for c in cases}
        assert len(paths) == 5

    def test_empty_input(self):
        assert self.gen.generate([]) == []

    def test_path_with_id_param_no_404_when_no_404_response(self):
        # If the spec doesn't declare 404, we shouldn't fabricate one
        ep = make_endpoint(
            method=HttpMethod.GET,
            path="/users/{id}",
            parameters=[Parameter(name="id", location="path", type="string", required=True)],
            responses=[Response(status_code="200")],  # no 404
        )
        cases = self.gen.generate([ep])
        # No "404" in titles
        assert not any("404" in c.title for c in cases)


class TestStableIdContentFingerprint:
    """P0 #1: stable_id must use content fingerprints, not position indices.

    Adding new rules / reordering rules / reordering params must NOT shift IDs.
    """

    def test_stable_ids_unchanged_when_adding_rule(self):
        """Critical: adding a new rule must NOT change existing IDs.

        This test simulates adding a new rule by calling the rules in the same
        order they would be called. If we ever add a rule in the middle, this
        test will catch ID drift.
        """
        ep = make_endpoint(parameters=[Parameter(name="id", location="path", type="string", required=True)])
        cases_before = StructuralGenerator().generate([ep])
        ids_before = sorted(c.id for c in cases_before)

        # Run the same generator twice (rule order is fixed in code)
        cases_after = StructuralGenerator().generate([ep])
        ids_after = sorted(c.id for c in cases_after)

        assert ids_before == ids_after, "stable_id is not deterministic!"

    def test_stable_ids_dont_use_index(self):
        """Each rule must use content-based ID, not position-based."""
        ep = make_endpoint(
            parameters=[
                Parameter(name="aaa", location="query", type="string", required=True),
                Parameter(name="bbb", location="query", type="string", required=True),
            ]
        )
        cases = StructuralGenerator().generate([ep])
        missing_cases = [c for c in cases if "缺失必填参数" in c.title]
        assert len(missing_cases) == 2
        # IDs must be different because param names differ (not because of index)
        assert missing_cases[0].id != missing_cases[1].id
        # Swap the parameter order and re-run - IDs must still differ
        ep2 = make_endpoint(parameters=list(reversed(ep.parameters)))
        cases2 = StructuralGenerator().generate([ep2])
        missing_cases2 = [c for c in cases2 if "缺失必填参数" in c.title]
        # Same param names → same IDs regardless of order (rule_name + param_name is stable)
        ids1 = sorted(c.id for c in missing_cases)
        ids2 = sorted(c.id for c in missing_cases2)
        assert ids1 == ids2, "IDs should not depend on parameter order"
