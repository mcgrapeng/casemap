from __future__ import annotations

from casemap.models.testcase import CaseType, TestCase, TestStatus, TestStep


class TestEnums:
    def test_case_type_values(self):
        assert CaseType.POSITIVE == "positive"
        assert CaseType.NEGATIVE == "negative"
        assert CaseType.EDGE == "edge"
        assert CaseType.SECURITY == "security"

    def test_test_status_values(self):
        assert TestStatus.PENDING == "pending"
        assert TestStatus.PASSED == "passed"


class TestTestStep:
    def test_construct(self):
        s = TestStep(order=1, action="Click login", expected="Login page shown")
        assert s.order == 1


class TestTestCase:
    def test_minimal(self):
        c = TestCase(id="abc", type=CaseType.POSITIVE, title="Happy login")
        assert c.status == TestStatus.PENDING
        assert c.steps == []
        assert c.failure_note == ""
        assert c.tags == []

    def test_full(self):
        c = TestCase(
            id="x1",
            type=CaseType.NEGATIVE,
            title="Bad password",
            description="Wrong creds",
            steps=[TestStep(order=1, action="submit", expected="error shown")],
            endpoint_ref="POST /login",
            tags=["auth"],
            status=TestStatus.FAILED,
            failure_note="页面空白",
        )
        assert c.endpoint_ref == "POST /login"
        assert c.status == TestStatus.FAILED
        assert c.failure_note == "页面空白"

    def test_serialize_roundtrip(self):
        c = TestCase(id="y", type=CaseType.EDGE, title="t")
        s = c.model_dump_json()
        c2 = TestCase.model_validate_json(s)
        assert c2.id == c.id
        assert c2.type == c.type
        assert c2.title == c.title
