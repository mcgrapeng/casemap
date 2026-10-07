"""Structural test case generator - heuristic rules.

Generates positive/negative/edge/security cases from endpoint metadata alone,
deterministically, with zero external dependencies.

P0 #1 invariant: every ``stable_id(...)`` call uses content fingerprints
(``rule_name + param_name + bound value``), never ``str(i)`` from an
enumerate index. Adding or reordering rules / parameters must NOT shift
existing IDs (else users' stored progress in localStorage is lost).
"""

from __future__ import annotations

from casemap._internal.logger import get_logger
from casemap.models.endpoint import Endpoint, HttpMethod, Parameter
from casemap.models.ids import stable_id
from casemap.models.testcase import CaseType, TestCase, TestStatus, TestStep

_log = get_logger("generators.structural")

# Status codes that imply "resource doesn't exist"
_NOT_FOUND_CODES = {"404", "410"}
# Status codes that imply auth problems
_AUTH_CODES = {"401", "403"}
# Status codes that imply conflict / uniqueness violation
_CONFLICT_CODES = {"409"}


class StructuralGenerator:
    """Generate test cases from endpoint metadata using deterministic rules."""

    def generate(self, endpoints: list[Endpoint]) -> list[TestCase]:
        out: list[TestCase] = []
        for ep in endpoints:
            out.extend(self._rule_happy_path(ep))
            out.extend(self._rule_required_params(ep))
            out.extend(self._rule_path_param_404(ep))
            out.extend(self._rule_auth_required(ep))
            out.extend(self._rule_conflict(ep))
            out.extend(self._rule_constraint_boundaries(ep))
            out.extend(self._rule_delete_security(ep))
        _log.debug(
            "structural generator produced %d cases from %d endpoints", len(out), len(endpoints)
        )
        return out

    # --- individual rules ----------------------------------------------------

    def _rule_happy_path(self, ep: Endpoint) -> list[TestCase]:
        return [
            TestCase(
                id=stable_id(str(ep.method), ep.path, "rule", "happy-path"),
                type=CaseType.POSITIVE,
                title=f"{ep.summary or ep.path} - 正常路径",
                description=f"使用合法参数调用 {ep.method} {ep.path}，预期成功响应。",
                steps=[
                    TestStep(order=1, action="填写所有必填参数为合法值", expected="通过校验"),
                    TestStep(order=2, action="提交请求", expected="返回成功状态码"),
                ],
                endpoint_ref=f"{ep.method} {ep.path}",
                tags=list(ep.tags),
            )
        ]

    def _rule_required_params(self, ep: Endpoint) -> list[TestCase]:
        required: list[Parameter] = [p for p in ep.parameters if p.required]
        if ep.request_body and ep.request_body.required:
            required.append(ep.request_body)
        out: list[TestCase] = []
        for p in required:
            out.append(
                TestCase(
                    id=stable_id(str(ep.method), ep.path, "rule", "missing-req", "param", p.name),
                    type=CaseType.NEGATIVE,
                    title=f"{ep.summary or ep.path} - 缺失必填参数 {p.name}",
                    description=f"省略必填参数 {p.name!r}，预期返回参数错误。",
                    steps=[
                        TestStep(order=1, action=f"不填写 {p.name}", expected="请求被拒绝"),
                    ],
                    endpoint_ref=f"{ep.method} {ep.path}",
                    tags=list(ep.tags),
                )
            )
        return out

    def _rule_path_param_404(self, ep: Endpoint) -> list[TestCase]:
        path_params = [p for p in ep.parameters if p.location == "path"]
        codes = {r.status_code for r in ep.responses}
        if not path_params or not (_NOT_FOUND_CODES & codes):
            return []
        code = next(iter(_NOT_FOUND_CODES & codes))
        return [
            TestCase(
                id=stable_id(str(ep.method), ep.path, "rule", "not-found"),
                type=CaseType.NEGATIVE,
                title=f"{ep.summary or ep.path} - 资源不存在",
                description=f"使用不存在的 ID 调用，预期返回 {code}。",
                steps=[
                    TestStep(order=1, action="使用不存在的 ID 发起请求", expected=f"返回 {code}"),
                ],
                endpoint_ref=f"{ep.method} {ep.path}",
                tags=list(ep.tags),
            )
        ]

    def _rule_auth_required(self, ep: Endpoint) -> list[TestCase]:
        # We don't know if the endpoint requires auth from the spec alone (it's
        # declared at the top level in OpenAPI). Heuristic: most non-GET on a
        # path that's not /health, /login, etc., likely requires auth.
        if ep.method == HttpMethod.GET and not any(p.required for p in ep.parameters):
            return []
        # Only emit if at least one of 401/403 is declared as a response code
        codes = {r.status_code for r in ep.responses}
        if not (_AUTH_CODES & codes):
            return []
        return [
            TestCase(
                id=stable_id(str(ep.method), ep.path, "rule", "no-auth"),
                type=CaseType.NEGATIVE,
                title=f"{ep.summary or ep.path} - 未授权访问",
                description="不提供凭证调用，预期返回 401 或 403。",
                steps=[
                    TestStep(order=1, action="不带凭证发起请求", expected="返回鉴权失败"),
                ],
                endpoint_ref=f"{ep.method} {ep.path}",
                tags=list(ep.tags),
            )
        ]

    def _rule_conflict(self, ep: Endpoint) -> list[TestCase]:
        if ep.method != HttpMethod.POST:
            return []
        codes = {r.status_code for r in ep.responses}
        if not (_CONFLICT_CODES & codes):
            return []
        return [
            TestCase(
                id=stable_id(str(ep.method), ep.path, "rule", "conflict"),
                type=CaseType.NEGATIVE,
                title=f"{ep.summary or ep.path} - 资源冲突",
                description="创建已存在的资源，预期返回 409。",
                steps=[
                    TestStep(order=1, action="创建一个已存在的资源", expected="返回 409"),
                ],
                endpoint_ref=f"{ep.method} {ep.path}",
                tags=list(ep.tags),
            )
        ]

    def _rule_constraint_boundaries(self, ep: Endpoint) -> list[TestCase]:
        out: list[TestCase] = []
        for p in ep.parameters:
            c = p.constraints
            if "minimum" in c and "maximum" in c:
                min_v, max_v = c["minimum"], c["maximum"]
                out.append(
                    TestCase(
                        id=stable_id(
                            str(ep.method),
                            ep.path,
                            "rule",
                            "edge-min",
                            "param",
                            p.name,
                            "bound",
                            str(min_v),
                        ),
                        type=CaseType.EDGE,
                        title=f"{ep.summary or ep.path} - 参数 {p.name} 最小值",
                        description=f"{p.name} 取最小值 {min_v}，预期正常。",
                        steps=[
                            TestStep(order=1, action=f"将 {p.name} 设为 {min_v}", expected="通过"),
                        ],
                        endpoint_ref=f"{ep.method} {ep.path}",
                        tags=list(ep.tags),
                    )
                )
                out.append(
                    TestCase(
                        id=stable_id(
                            str(ep.method),
                            ep.path,
                            "rule",
                            "edge-max",
                            "param",
                            p.name,
                            "bound",
                            str(max_v),
                        ),
                        type=CaseType.EDGE,
                        title=f"{ep.summary or ep.path} - 参数 {p.name} 最大值",
                        description=f"{p.name} 取最大值 {max_v}，预期正常。",
                        steps=[
                            TestStep(order=1, action=f"将 {p.name} 设为 {max_v}", expected="通过"),
                        ],
                        endpoint_ref=f"{ep.method} {ep.path}",
                        tags=list(ep.tags),
                    )
                )
                out.append(
                    TestCase(
                        id=stable_id(
                            str(ep.method),
                            ep.path,
                            "rule",
                            "edge-overflow",
                            "param",
                            p.name,
                        ),
                        type=CaseType.EDGE,
                        title=f"{ep.summary or ep.path} - 参数 {p.name} 越界",
                        description=f"{p.name} 超过最大值 {max_v}，预期被拒绝。",
                        steps=[
                            # ponytail: only emit overflow case if max_v is
                            # numeric. String "100" (legal JSON, valid schema
                            # declaration) would TypeError on +1.
                            TestStep(
                                order=1,
                                action=(
                                    f"将 {p.name} 设为 {int(max_v) + 1}"
                                    if isinstance(max_v, (int, float))
                                    and not isinstance(max_v, bool)
                                    else f"将 {p.name} 设为超过最大值 {max_v} 的非法值"
                                ),
                                expected="返回参数错误",
                            ),
                        ],
                        endpoint_ref=f"{ep.method} {ep.path}",
                        tags=list(ep.tags),
                    )
                )
            if p.type == "string":
                out.append(
                    TestCase(
                        id=stable_id(
                            str(ep.method),
                            ep.path,
                            "rule",
                            "edge-empty-string",
                            "param",
                            p.name,
                        ),
                        type=CaseType.EDGE,
                        title=f"{ep.summary or ep.path} - 参数 {p.name} 为空字符串",
                        description=f"将 {p.name} 设为空串，预期行为合理。",
                        steps=[
                            TestStep(
                                order=1, action=f"将 {p.name} 留空", expected="合理的拒绝或自动填充"
                            ),
                        ],
                        endpoint_ref=f"{ep.method} {ep.path}",
                        tags=list(ep.tags),
                    )
                )
        return out

    def _rule_delete_security(self, ep: Endpoint) -> list[TestCase]:
        if ep.method != HttpMethod.DELETE:
            return []
        return [
            TestCase(
                id=stable_id(str(ep.method), ep.path, "rule", "delete-security"),
                type=CaseType.SECURITY,
                title=f"{ep.summary or ep.path} - 删除操作的权限检查",
                description="确认普通用户无法删除他人资源。",
                steps=[
                    TestStep(order=1, action="用普通用户身份尝试删除他人资源", expected="被拒绝"),
                ],
                endpoint_ref=f"{ep.method} {ep.path}",
                tags=list(ep.tags),
            )
        ]


__all__ = ["StructuralGenerator"]


if __name__ == "__main__":  # pragma: no cover
    # ponytail: one-shot self-check, no framework.
    from casemap.models.endpoint import Response

    sample = Endpoint(
        path="/users/{id}",
        method=HttpMethod.GET,
        parameters=[Parameter(name="id", location="path", type="string", required=True)],
        responses=[Response(status_code="200"), Response(status_code="404")],
    )
    cases = StructuralGenerator().generate([sample])
    assert any(c.type == CaseType.POSITIVE for c in cases)
    assert any(c.type == CaseType.NEGATIVE for c in cases)
    assert TestStatus.PENDING in {c.status for c in cases}
    # re-run: IDs must match
    again = StructuralGenerator().generate([sample])
    assert sorted(c.id for c in cases) == sorted(c.id for c in again), "stable_id drift!"
    print(f"OK: {len(cases)} cases, ids stable")
