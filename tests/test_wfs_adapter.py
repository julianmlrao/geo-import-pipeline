import pytest
import responses

from geo_import import http
from geo_import.adapters.wfs import WfsAdapter
from geo_import.config import parse_source
from tests.helpers import gml_collection

URL = "https://example.test/wfs"


def cfg(**kw):
    return parse_source(
        {
            "source_id": "g",
            "title": "t",
            "type": "wfs",
            "url": URL,
            "layer": "app:gem",
            "feature_key": "ags",
            "page_size": 2,
            **kw,
        }
    )


@responses.activate
def test_paging_until_short_page():
    items = [(f"g{i}", f"1200{i}", f"G{i}", (300000 + i * 2000, 5800000)) for i in range(5)]
    for start in (0, 2, 4):
        responses.add(
            responses.GET,
            URL,
            body=gml_collection(items[start : start + 2]),
            match=[
                responses.matchers.query_param_matcher(
                    {
                        "SERVICE": "WFS",
                        "VERSION": "2.0.0",
                        "REQUEST": "GetFeature",
                        "TYPENAMES": "app:gem",
                        "STARTINDEX": str(start),
                        "COUNT": "2",
                    }
                )
            ],
        )
    feats = list(WfsAdapter(cfg()).fetch())
    assert [f.properties["ags"] for f in feats] == [f"1200{i}" for i in range(5)]
    assert feats[0].geometry.bounds[0] == 300000  # still source CRS
    assert feats[0].properties["gem_name"] == "G0"


@responses.activate
def test_server_ignoring_startindex_stops_with_warning():
    page = gml_collection([("g0", "1", "A", (0, 0)), ("g1", "2", "B", (0, 0))])
    responses.add(responses.GET, URL, body=page)
    ad = WfsAdapter(cfg())
    assert len(list(ad.fetch())) == 2
    assert any("STARTINDEX" in w for w in ad.stats.warnings)


@responses.activate
def test_wfs_exception_report_raises():
    responses.add(
        responses.GET,
        URL,
        body=b'<ows:ExceptionReport xmlns:ows="http://www.opengis.net/ows/1.1"><ows:Exception><ows:ExceptionText>Unknown type</ows:ExceptionText></ows:Exception></ows:ExceptionReport>',
    )
    with pytest.raises(http.FetchError, match="Unknown type"):
        list(WfsAdapter(cfg()).fetch())


@responses.activate
def test_retries_then_fails(monkeypatch):
    monkeypatch.setattr(http.time, "sleep", lambda s: None)
    responses.add(responses.GET, URL, status=503)
    with pytest.raises(http.FetchError, match="after 4 attempts"):
        list(WfsAdapter(cfg()).fetch())
    assert len(responses.calls) == 4


@responses.activate
def test_geojson_output():
    responses.add(
        responses.GET,
        URL,
        json={
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "id": "1",
                    "properties": {"ags": "1"},
                    "geometry": {"type": "Point", "coordinates": [13, 52]},
                }
            ],
        },
    )
    feats = list(WfsAdapter(cfg(output_format="geojson")).fetch())
    assert feats[0].geometry.x == 13
