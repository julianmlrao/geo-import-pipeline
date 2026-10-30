from geo_import.adapters.csv import CsvAdapter, decode, detect_delimiter
from geo_import.config import parse_source


def test_decode_utf8_bom_and_cp1252_fallback():
    assert decode("Müller".encode("utf-8-sig"), None)[0] == "Müller"
    text, enc = decode("Cottbus/Chóśebuz größe".encode("cp1252", errors="replace"), None)
    assert enc in ("cp1252", "utf-8-sig")
    assert decode("Müller".encode("cp1252"), None) == ("Müller", "cp1252")


def test_delimiter_detection():
    assert detect_delimiter("a;b;c\n1;2;3") == ";"
    assert detect_delimiter("a,b,c\n1,2,3") == ","
    assert detect_delimiter("a\tb\n1\t2") == "\t"


def test_csv_lonlat_and_skip_rows(tmp_path):
    p = tmp_path / "x.csv"
    p.write_bytes("Titel der Datei\nid;lon;lat\n1;13,5;52,5\n".encode("cp1252"))
    cfg = parse_source(
        {
            "source_id": "x",
            "title": "t",
            "type": "csv",
            "url": str(p),
            "feature_key": "id",
            "skip_rows": 1,
            "lon_column": "lon",
            "lat_column": "lat",
            "decimal": ",",
        }
    )
    feats = list(CsvAdapter(cfg).fetch())
    assert len(feats) == 1 and (feats[0].geometry.x, feats[0].geometry.y) == (13.5, 52.5)


def test_csv_wkt(tmp_path):
    p = tmp_path / "x.csv"
    p.write_text("id,wkt\n1,POINT (13 52)\n", encoding="utf-8")
    cfg = parse_source(
        {
            "source_id": "x",
            "title": "t",
            "type": "csv",
            "url": str(p),
            "feature_key": "id",
            "wkt_column": "wkt",
        }
    )
    assert list(CsvAdapter(cfg).fetch())[0].geometry.wkt == "POINT (13 52)"
