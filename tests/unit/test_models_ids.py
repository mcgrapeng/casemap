from __future__ import annotations

import re

from casemap.models.ids import stable_id

HEX16 = re.compile(r"^[0-9a-f]{16}$")


def test_deterministic():
    a = stable_id("POST", "/users", "positive", "0")
    b = stable_id("POST", "/users", "positive", "0")
    assert a == b


def test_format():
    assert HEX16.match(stable_id("x"))


def test_different_inputs_different_ids():
    assert stable_id("a") != stable_id("b")


def test_collision_resistant():
    ids = {stable_id(f"endpoint-{i}", "GET", "positive") for i in range(100)}
    assert len(ids) == 100


def test_order_matters():
    assert stable_id("a", "b") != stable_id("b", "a")


def test_empty_inputs():
    # Even empty inputs must produce a valid id (use defaults)
    a = stable_id()
    b = stable_id()
    assert HEX16.match(a)
    assert HEX16.match(b)
