import pytest
from app.sanitizer import sanitize_html


def test_sanitize_strips_script_tags():
    raw = "<div><h3>Growth Framework</h3><script>alert('malicious')</script><p>Safe content</p></div>"
    clean = sanitize_html(raw)
    assert "<script>" not in clean
    assert "alert('malicious')" not in clean
    assert "<h3>Growth Framework</h3>" in clean
    assert "<p>Safe content</p>" in clean


def test_sanitize_strips_inline_event_handlers():
    raw = '<button onclick="evilCode()" onmouseover="stealTokens()">Click me</button><div onerror="doSomething()">Alert</div>'
    clean = sanitize_html(raw)
    assert "onclick" not in clean
    assert "onmouseover" not in clean
    assert "onerror" not in clean
    assert "evilCode" not in clean
    # button is also in DISALLOWED_TAGS, so it shouldn't produce a button tag
    assert "<button" not in clean
    assert "<div>Alert</div>" in clean


def test_sanitize_strips_javascript_href_and_src():
    raw = '<a href="javascript:alert(1)">Click</a><img src="javascript:evil()" alt="test" /><img src="https://example.com/image.png" alt="valid" />'
    clean = sanitize_html(raw)
    assert "javascript:" not in clean
    assert 'href=' not in clean or 'href="javascript:' not in clean
    assert 'alt="valid"' in clean


def test_sanitize_strips_iframe_and_object():
    raw = "<div><iframe src='http://evil.com'></iframe><object data='evil.swf'></object><p>Legitimate insight</p></div>"
    clean = sanitize_html(raw)
    assert "<iframe" not in clean
    assert "<object" not in clean
    assert "<p>Legitimate insight</p>" in clean


def test_sanitize_allows_safe_formatting_and_css():
    raw = '<div class="card" style="padding: 16px;"><h2 class="title">Retention Curve</h2><table class="data-table"><thead><tr><th>Metric</th><th>Target</th></tr></thead><tbody><tr><td>D30 Retention</td><td>40%</td></tr></tbody></table></div>'
    clean = sanitize_html(raw)
    assert '<div class="card" style="padding: 16px;">' in clean
    assert '<h2 class="title">Retention Curve</h2>' in clean
    assert '<table class="data-table">' in clean
    assert '<td>D30 Retention</td>' in clean
