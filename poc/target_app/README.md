# Impact Analysis POC Target

This disposable billing application gives the Change Impact Analysis Agent a
small but realistic repository to inspect. It includes layered Python code, an
upstream consumer, SQL schema, OpenAPI contract, architecture documentation,
and deterministic tests. It is intentionally not a production service.

The matching Low, Medium, and High risk issue bodies live in the parent
impact-analysis repository under `poc/issues/`.

## Local validation

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[test]'
pytest
ruff check .
```
