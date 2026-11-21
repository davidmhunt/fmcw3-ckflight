"""parts/check_digikey.py on recorded-shape responses: no network, no keys.

The fixtures follow the DigiKey Product Information v4 keyword-search schema, trimmed to the
fields the module reads. They contain no headers, tokens or credentials.
"""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "parts"))
import check_digikey as dk  # noqa: E402


def product(mpn, status="Active", stock=1000, pkg="0402", params=None, pn="X-ND",
            breaks=((1, 0.10), (100, 0.04), (1000, 0.02)), lead="8"):
    return {
        "ManufacturerProductNumber": mpn,
        "Manufacturer": {"Name": "Acme"},
        "ProductStatus": {"Status": status},
        "QuantityAvailable": stock,
        "ManufacturerLeadWeeks": lead,
        "DatasheetUrl": f"https://example.com/{mpn}.pdf",
        "ProductUrl": f"https://www.digikey.com/p/{mpn}",
        "Parameters": [{"ParameterText": "Package / Case", "ValueText": f"{pkg} (1005 Metric)"}]
        + (params or []),
        "ProductVariations": [
            {"DigiKeyProductNumber": pn + "-TR", "PackageType": {"Name": "Tape & Reel (TR)"},
             "StandardPricing": [{"BreakQuantity": 10000, "UnitPrice": 0.01}]},
            {"DigiKeyProductNumber": pn, "PackageType": {"Name": "Cut Tape (CT)"},
             "StandardPricing": [{"BreakQuantity": q, "UnitPrice": u} for q, u in breaks]},
        ],
    }


def cap(mpn, value="0.1 µF", tol="±10%", volt="16V", tc="X7R", **kw):
    return product(mpn, params=[{"ParameterText": "Capacitance", "ValueText": value},
                                {"ParameterText": "Tolerance", "ValueText": tol},
                                {"ParameterText": "Voltage - Rated", "ValueText": volt},
                                {"ParameterText": "Temperature Coefficient", "ValueText": tc}],
                   **kw)


class FakeTransport:
    """Records calls; answers token requests and keyword searches from a dict."""

    def __init__(self, answers):
        self.answers, self.calls = answers, []

    def __call__(self, url, data, headers):
        self.calls.append((url, data, headers))
        if url.endswith("/oauth2/token"):
            return {"access_token": "T0KEN"}
        kw = json.loads(data)["Keywords"]
        return {"Products": self.answers.get(kw, [])}


def client(answers):
    t = FakeTransport(answers)
    return dk.Client("CID", "SECRET", transport=t, delay=0), t


def grp(**kw):
    g = {"Value": "", "Footprint": "SMD_0402", "MPN": "", "DigiKey PN": "", "class": "mpn",
         "refs": ["U1"], "qty": 1}
    g.update(kw)
    return g


# ---- env

def test_load_env_reads_file_and_env_wins(tmp_path, monkeypatch):
    f = tmp_path / ".env"
    f.write_text("# c\nDIGIKEY_CLIENT_ID='abc'\nDIGIKEY_CLIENT_SECRET=def\nOTHER=1\n")
    monkeypatch.delenv("DIGIKEY_CLIENT_ID", raising=False)  # hermetic: ./run may pass real keys
    monkeypatch.setenv("DIGIKEY_CLIENT_SECRET", "fromenv")
    env = dk.load_env(f)
    assert env["DIGIKEY_CLIENT_ID"] == "abc"
    assert env["DIGIKEY_CLIENT_SECRET"] == "fromenv"
    assert "OTHER" in env


def test_require_keys_names_the_missing_ones_only():
    with pytest.raises(dk.DigiKeyError) as e:
        dk.require_keys({"DIGIKEY_CLIENT_ID": "x"})
    assert "Missing DIGIKEY_CLIENT_SECRET:" in str(e.value)


# ---- parsing

def test_lifecycle_buckets():
    assert dk.lifecycle("Active") == "Active"
    assert dk.lifecycle("Not For New Designs") == "NFND"
    assert dk.lifecycle("Last Time Buy") == "NFND"
    assert dk.lifecycle("Obsolete") == "Obsolete"
    assert dk.lifecycle("Discontinued at Digi-Key") == "Obsolete"


def test_price_break_selection():
    p = product("A")
    assert dk.price_at(p, 1) == 0.10
    assert dk.price_at(p, 99) == 0.10
    assert dk.price_at(p, 100) == 0.04
    assert dk.price_at(p, 5000) == 0.02   # tape-and-reel break (10000) is not the cut-tape one
    assert dk.price_at({"ProductVariations": []}, 5) is None


def test_parse_product_fields():
    r = dk.parse_product(product("A", stock=50), 30)
    assert r["dk_status"] == "Active" and r["dk_stock"] == 50
    assert r["dk_unit_price"] == 0.10 and r["dk_price_qty"] == 30
    assert r["dk_pn"] == "X-ND" and r["dk_lead_weeks"] == "8"
    assert r["dk_datasheet"].endswith("A.pdf") and r["dk_lifecycle"] == "Active"


def test_parse_product_low_stock_and_obsolete():
    assert dk.parse_product(product("A", stock=5), 30)["dk_status"] == "Low stock"
    r = dk.parse_product(product("A", status="Obsolete"), 3)
    assert r["dk_status"] == "Obsolete" and r["dk_lifecycle"] == "Obsolete"
    assert dk.parse_product(product("A", status="Not For New Designs"), 1)["dk_status"] == "NFND"


# ---- MPN lines

def test_mpn_exact_match_case_insensitive():
    c, t = client({"adf4159ccpz": [product("ADF4159CCPZ-RL7"), product("ADF4159CCPZ", stock=12)]})
    r = dk.check_group(c, grp(MPN="adf4159ccpz"), 6)
    assert r["dk_match"] == "exact" and r["dk_mpn"] == "ADF4159CCPZ" and r["dk_stock"] == 12
    assert r["dk_status"] == "Active"


def test_mpn_no_result_when_only_near_matches():
    c, _ = client({"FOO": [product("FOO-1")]})
    r = dk.check_group(c, grp(MPN="FOO"), 3)
    assert r["dk_status"] == "No-result" and r["dk_stock"] == 0


def test_mpn_found_by_digikey_pn():
    c, _ = client({"X-ND": [product("Z1", pn="X-ND")]})
    r = dk.check_group(c, grp(**{"DigiKey PN": "X-ND"}), 1)
    assert r["dk_mpn"] == "Z1"


def test_dnp_and_nopart_do_not_search():
    c, t = client({})
    assert dk.check_group(c, grp(**{"class": "dnp"}), 3)["dk_status"] == "n/a"
    assert dk.check_group(c, grp(**{"class": "nopart"}), 3)["dk_status"] == "n/a"
    assert t.calls == []


# ---- generic passives

def test_value_text_and_package():
    assert dk.value_text("C", "100n") == "100nF"
    assert dk.value_text("C", "10u") == "10µF"
    assert dk.value_text("C", "2.2n") == "2.2nF"
    assert dk.value_text("R", "10k") == "10kOhm"
    assert dk.value_text("R", "49.9") == "49.9Ohm"
    assert dk.value_text("L", "3.3n") == "3.3nH"
    assert dk.package_code("SMD_0402") == "0402"
    assert dk.package_code("C_0805_2012Metric") == "0805"
    assert dk.package_code("SOT-23") == ""


def test_to_base_handles_digikey_spellings():
    assert dk.to_base("0.1 µF") == pytest.approx(1e-7)
    assert dk.to_base("100nF") == pytest.approx(1e-7)
    assert dk.to_base("10 kOhms") == pytest.approx(1e4)
    assert dk.to_base("2.2 nH") == pytest.approx(2.2e-9)


def test_parametric_query_includes_only_specified_fields():
    g = grp(**{"class": "generic"}, Value="100n", refs=["C1"], Dielectric="X7R", Voltage="16V")
    q, spec = dk.parametric_query(g)
    assert q == "100nF 0402 ceramic capacitor X7R 16V"
    assert spec["tolerance"] == ""


def test_generic_suggests_best_match():
    g = grp(**{"class": "generic"}, Value="100n", refs=["C1", "C2"], qty=2, Tolerance="10%",
            Voltage="16V", Dielectric="X7R")
    q, _ = dk.parametric_query(g)
    answers = {q: [
        cap("WRONGVAL", value="1 µF"),                        # wrong value
        cap("WRONGPKG", ),                                     # fixed below
        cap("OBS", status="Obsolete"),
        cap("NOSTOCK", stock=1),
        cap("LOWSPEC", volt="6.3V", tc="X5R", tol="±20%"),
        cap("BEST", stock=500),
    ]}
    answers[q][1]["Parameters"][0]["ValueText"] = "0603 (1608 Metric)"
    c, _ = client(answers)
    r = dk.check_group(c, g, 30)
    assert r["dk_status"] == "Suggested" and r["dk_match"] == "parametric"
    assert r["dk_suggested_mpn"] == "BEST"
    assert r["dk_query"] == q and r["dk_unit_price"] == 0.10


def test_generic_resistor_matches_ohms():
    g = grp(**{"class": "generic"}, Value="10k", refs=["R1"])
    q, _ = dk.parametric_query(g)
    res = product("R10K", params=[{"ParameterText": "Resistance", "ValueText": "10 kOhms"},
                                  {"ParameterText": "Tolerance", "ValueText": "±1%"}])
    c, _ = client({q: [res]})
    assert dk.check_group(c, g, 3)["dk_suggested_mpn"] == "R10K"


def test_generic_no_match():
    g = grp(**{"class": "generic"}, Value="100n", refs=["C1"])
    q, _ = dk.parametric_query(g)
    c, _ = client({q: [cap("OBS", status="Obsolete")]})
    r = dk.check_group(c, g, 3)
    assert r["dk_status"] == "No-match" and r["dk_suggested_mpn"] == ""


# ---- credentials never leak

def test_token_requested_once_and_secrets_stay_in_requests_only():
    c, t = client({"A": [product("A")]})
    dk.check_group(c, grp(MPN="A"), 1)
    dk.check_group(c, grp(MPN="A"), 1)
    assert sum(u.endswith("/oauth2/token") for u, _, _ in t.calls) == 1
    out = dk.check_group(c, grp(MPN="A"), 1)
    assert "SECRET" not in json.dumps(out) and "T0KEN" not in json.dumps(out)


def test_http_error_message_has_no_credentials(monkeypatch):
    import urllib.error

    def boom(req, timeout=0):
        raise urllib.error.HTTPError(req.full_url, 401, "x", {}, __import__("io").BytesIO(b"denied"))

    monkeypatch.setattr(dk.urllib.request, "urlopen", boom)
    c = dk.Client("CID", "SECRET", delay=0)
    with pytest.raises(dk.DigiKeyError) as e:
        c.token()
    assert "SECRET" not in str(e.value) and "401" in str(e.value)
