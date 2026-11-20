"""docs/analysis-tools.md has its required sections and cites only manifest ids that exist.

A test rather than a grep in Verify: the bash_file_io hook denies a Verify line that reads files.
A manifest id is cited as a backticked token in the `## References` section.
"""
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "analysis-tools.md"
MANIFESTS = ("datasheets/manifest.yaml", "docs/references/manifest.yaml")
SECTIONS = ("## Verdict", "## Tools the user must obtain", "## References")


def manifest_ids():
    ids = set()
    for rel in MANIFESTS:
        data = yaml.safe_load((ROOT / rel).read_text()) or {}
        ids |= {e["id"] for e in data.get("entries") or []}
    return ids


def section(text, heading):
    m = re.search(rf"^{re.escape(heading)}\s*$(.*?)(?=^## |\Z)", text, re.S | re.M)
    return m.group(1) if m else None


def test_required_sections_present():
    text = DOC.read_text()
    headings = set(re.findall(r"^## .*$", text, re.M))
    missing = [s for s in SECTIONS if s not in headings]
    assert not missing, f"docs/analysis-tools.md lacks {missing}"


def test_cited_manifest_ids_exist():
    refs = section(DOC.read_text(), "## References")
    assert refs is not None, "no ## References section"
    cited = set(re.findall(r"`([A-Za-z0-9][A-Za-z0-9._-]*)`", refs))
    assert cited, "## References cites no manifest id (expected backticked ids)"
    unknown = sorted(cited - manifest_ids())
    assert not unknown, f"ids cited in ## References but in no manifest: {unknown}"


def test_cited_ids_have_verified_items():
    refs = section(DOC.read_text(), "## References")
    cited = set(re.findall(r"`([A-Za-z0-9][A-Za-z0-9._-]*)`", refs))
    verified = set()
    for rel in MANIFESTS:
        data = yaml.safe_load((ROOT / rel).read_text()) or {}
        verified |= {e["id"] for e in data.get("entries") or [] if e.get("verified")}
    missing = sorted(cited - verified)
    assert not missing, f"ids in ## References with no verified item: {missing}"
