"""MANUAL.md must cover every ./run mode, software download and command-line tool."""
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
MANUAL = (ROOT / "MANUAL.md").read_text()


def _run_modes():
    """Mode flags from the usage lines at the top of the run script."""
    usage = []
    for line in (ROOT / "run").read_text().splitlines():
        if not line.startswith("#"):
            break
        if "./run" in line:
            usage.append(line)
    modes = set(re.findall(r"--[a-z][a-z-]*", " ".join(usage)))
    modes -= {"--print"}  # an option of --sim-gui, not a mode
    return sorted(modes)


def _manual_section(title):
    m = re.search(rf"^## [^\n]*{re.escape(title)}[^\n]*\n(.*?)(?=^## |\Z)", MANUAL, re.S | re.M)
    assert m, f"MANUAL.md has no section about {title!r}"
    return m.group(1)


def test_run_modes_found():
    assert {"--docker", "--native", "--sim", "--sim-gui"} <= set(_run_modes())


def test_every_run_mode_in_manual():
    missing = [m for m in _run_modes() if f"`./run {m}" not in MANUAL]
    assert not missing, f"./run modes missing from MANUAL.md: {missing}"


def test_every_software_id_in_downloads_table():
    entries = yaml.safe_load((ROOT / "software/manifest.yaml").read_text())["entries"]
    section = _manual_section("Software downloads")
    rows = [ln for ln in section.splitlines() if ln.startswith("|")]
    missing = [e["id"] for e in entries if not any(f"`{e['id']}`" in r for r in rows)]
    assert not missing, f"software ids missing from the downloads table: {missing}"


def _cli_tools(folder):
    return [
        p
        for p in sorted((ROOT / folder).glob("*.py"))
        if '__name__ == "__main__"' in p.read_text() or "__name__ == '__main__'" in p.read_text()
    ]


def test_every_cli_tool_named():
    tools = _cli_tools("tools")
    assert tools, "no command-line tools found"
    missing = [f"tools/{p.name}" for p in tools if f"tools/{p.name}" not in MANUAL]
    assert not missing, f"tools missing from MANUAL.md: {missing}"


def test_every_parts_tool_named():
    tools = _cli_tools("parts")
    assert {"bom.py", "check_digikey.py", "check_jlc.py"} <= {p.name for p in tools}
    section = _manual_section("Parts and availability")
    missing = [f"parts/{p.name}" for p in tools if f"parts/{p.name}" not in section]
    assert not missing, f"parts tools missing from the Parts and availability section: {missing}"


def test_relative_links_resolve():
    broken = []
    for target in re.findall(r"\]\(([^)\s]+)\)", MANUAL):
        if re.match(r"[a-z]+:", target) or target.startswith("#"):
            continue
        path = target.split("#")[0]
        if not (ROOT / path).exists():
            broken.append(target)
    assert not broken, f"broken relative links in MANUAL.md: {broken}"
