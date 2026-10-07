from __future__ import annotations

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from casemap.generators.structural import StructuralGenerator
from casemap.models.endpoint import Endpoint, HttpMethod, Parameter, Response


@st.composite
def endpoints(draw):
    method = draw(st.sampled_from(list(HttpMethod)))
    path = draw(st.sampled_from(["/a", "/a/{id}", "/b", "/users", "/posts/{pid}"]))
    has_param = draw(st.booleans())
    params = []
    if has_param:
        params.append(
            Parameter(
                name="id",
                location="path" if "{id}" in path else "query",
                type="string",
                required=draw(st.booleans()),
                constraints={"minimum": 1, "maximum": 100} if draw(st.booleans()) else {},
            )
        )
    responses = draw(
        st.lists(
            st.sampled_from(
                [
                    Response(status_code="200"),
                    Response(status_code="400"),
                    Response(status_code="404"),
                ]
            ),
            min_size=1,
            max_size=3,
        )
    )
    return Endpoint(path=path, method=method, parameters=params, responses=responses)


def test_always_has_at_least_one_positive():
    gen = StructuralGenerator()
    for ep in [Endpoint(path="/x", method=HttpMethod.GET, responses=[Response(status_code="200")])]:
        cases = gen.generate([ep])
        assert any(c.type.value == "positive" for c in cases)


@given(endpoints())
@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=50)
def test_each_endpoint_yields_at_least_one_positive(ep):
    gen = StructuralGenerator()
    cases = gen.generate([ep])
    assert any(c.type.value == "positive" for c in cases)


@given(endpoints())
@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=50)
def test_all_ids_unique(ep):
    gen = StructuralGenerator()
    cases = gen.generate([ep])
    ids = [c.id for c in cases]
    assert len(ids) == len(set(ids))


@given(endpoints())
@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=30)
def test_idempotent(ep):
    gen = StructuralGenerator()
    a = sorted(c.id for c in gen.generate([ep]))
    b = sorted(c.id for c in gen.generate([ep]))
    assert a == b
