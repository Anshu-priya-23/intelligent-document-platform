import hashlib
import re
from urllib.parse import urlsplit, parse_qs
import pytest
from backend.app.main import ROOT

@pytest.mark.parametrize("route", ["/", "/document"])
def test_templates_render_versioned_assets(client, route):
    response = client.get(route)
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-cache"
    assert "{{" not in response.text
    urls = re.findall(r'(?:href|src)="([^"]+/static/[^"]+)"', response.text)
    assert len(urls) == 2
    for url in urls:
        parts = urlsplit(url)
        asset = parts.path.removeprefix("/static/")
        expected = (ROOT / "frontend/static" / asset).read_bytes()
        assert parse_qs(parts.query)["v"] == [hashlib.sha256(expected).hexdigest()[:16]]
        result = client.get(url)
        assert result.status_code == 200 and result.content == expected
        assert result.headers["content-type"].startswith("text/css" if asset.endswith("css") else "text/javascript")
    assert response.text.index('rel="stylesheet"') < response.text.index('<script defer')


def test_original_static_paths_remain_supported(client):
    assert client.get("/static/css/app.css").status_code == 200
    assert client.get("/static/js/app.js").status_code == 200
    css = client.get("/static/css/app.css").text
    assert ".sidebar" in css and ".stats" in css and "--indigo" in css
