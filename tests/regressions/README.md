# Regression Tests

Use this folder only for cross-cutting regression tests that do not clearly belong beside one route,
model, or utility test file.

Prefer placing regression tests next to the feature they protect. Mark every regression test with:

```python
@pytest.mark.regression
```

Name tests after the behavior:

```python
def test_sitemap_index_keeps_www_canonical_urls_after_domain_redirect():
    ...
```

Avoid naming tests only after an issue number. If an issue number matters, mention it in a short
comment above the assertion that protects the fixed behavior.
