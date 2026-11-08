"""Contract tests: the spec is the contract, and these check the code against it.

Schemathesis reads openapi.yaml and generates requests, including inputs the
unit tests did not think of. The drift test checks that /openapi.json and
openapi.yaml declare the same operations once the /v1 prefix is applied.
"""

import re

import schemathesis
import yaml
from hypothesis import HealthCheck, settings

from app.main import app

SPEC_PATH = "openapi.yaml"

schema = schemathesis.openapi.from_path(SPEC_PATH)
schema.app = app
schema.config.update(base_url="http://testserver/v1")


@schema.parametrize()
@settings(max_examples=25, deadline=None, suppress_health_check=[HealthCheck.too_slow, HealthCheck.data_too_large])
def test_api_keeps_the_contract(case):
    case.call_and_validate()


def _base_path(spec: dict) -> str:
    """The path part of servers[0].url with its variables filled from their defaults."""
    server = spec["servers"][0]
    url = server["url"]
    for name, var in server.get("variables", {}).items():
        url = url.replace("{" + name + "}", var["default"])
    path = re.sub(r"^https?://[^/]+", "", url)
    return path.rstrip("/")


METHODS = {"get", "post", "put", "patch", "delete", "head", "options"}


def _operations(paths: dict, prefix: str = "") -> set[tuple[str, str]]:
    return {
        (prefix + path, method.upper())
        for path, item in paths.items()
        for method in item
        if method in METHODS
    }


def test_code_and_spec_declare_the_same_operations(client):
    with open(SPEC_PATH, encoding="utf-8") as handle:
        spec = yaml.safe_load(handle)
    declared = _operations(spec["paths"], prefix=_base_path(spec))

    generated = client.get("/openapi.json").json()
    implemented = _operations(generated["paths"])

    missing = declared - implemented
    extra = implemented - declared
    assert not missing, f"in the spec but not in the code: {sorted(missing)}"
    assert not extra, f"in the code but not in the spec: {sorted(extra)}"
