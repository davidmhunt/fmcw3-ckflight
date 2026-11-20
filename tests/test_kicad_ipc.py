"""Tests for tools/kicad_ipc.py using fake clients; no KiCad or kipy needed."""

import csv
import sys
from pathlib import Path
from types import SimpleNamespace as NS

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import kicad_ipc as k  # noqa: E402

PROJECT = Path("/work/proj/fmcw3.kicad_pro")


def ver(a, b, c):
    return NS(major=a, minor=b, patch=c)


class FakeKiCad:
    def __init__(self, kicad=(10, 0, 5), api=(10, 0, 6), docs=None, ping_ok=True):
        self._k, self._a = ver(*kicad), ver(*api)
        self._docs = docs or {}
        self.ping_ok = ping_ok

    def get_version(self):
        return self._k

    def get_api_version(self):
        return self._a

    def ping(self):
        if not self.ping_ok:
            raise RuntimeError("no answer")

    def get_open_documents(self, t):
        return self._docs.get(t, [])


def doc_for(project):
    p = Path(project)
    return NS(project=NS(path=str(p), name=p.stem))


class FakeEditor:
    """Records selection and commit calls; shared by fake board and schematic."""

    def __init__(self):
        self.calls = []
        self.selection = []

    def clear_selection(self):
        self.calls.append("clear_selection")
        self.selection = []

    def add_to_selection(self, items):
        self.calls.append("add_to_selection")
        self.selection.extend(items)

    def begin_commit(self):
        self.calls.append("begin_commit")
        return "C1"

    def push_commit(self, commit, message=""):
        self.calls.append("push_commit")

    def drop_commit(self, commit):
        self.calls.append("drop_commit")

    def update_items(self, items):
        self.calls.append("update_items")

    def save(self, *a, **kw):
        self.calls.append("save")

    def save_as(self, *a, **kw):
        self.calls.append("save_as")

    def revert(self, *a, **kw):
        self.calls.append("revert")


def text(v):
    return NS(value=v)


def field(name, v):
    return NS(name=name, text=text(v))


def sym(ref, kid, user=()):
    return NS(id=NS(value=kid), reference_field=field("Reference", ref),
              value_field=field("Value", "1k"), footprint_field=field("Footprint", ""),
              datasheet_field=field("Datasheet", ""), description_field=field("Description", ""),
              user_fields=list(user))


class FakeSch(FakeEditor):
    def __init__(self, symbols, labels=()):
        super().__init__()
        self.symbols, self.labels = symbols, list(labels)

    def get_symbols(self):
        return self.symbols

    def get_labels(self):
        return self.labels


class FakeBoard(FakeEditor):
    def __init__(self, footprints, nets, net_items):
        super().__init__()
        self.fps, self.nets, self.net_items = footprints, nets, net_items

    def get_footprints(self):
        return self.fps

    def get_nets(self):
        return self.nets

    def get_items_by_net(self, net):
        return self.net_items[net.name]


# ------------------------------------------------------------------ status

def test_status_closed():
    assert k.status(PROJECT, running_fn=lambda: False,
                    connect_fn=lambda: pytest.fail("must not connect")) == "closed"


def test_status_ipc_when_project_open():
    kc = FakeKiCad(docs={k.DOCTYPE_PCB: [doc_for(PROJECT)]})
    assert k.status(PROJECT, running_fn=lambda: True, connect_fn=lambda: kc) == "ipc"


def test_status_ipc_via_schematic_doc():
    kc = FakeKiCad(docs={k.DOCTYPE_SCHEMATIC: [doc_for(PROJECT)]})
    assert k.status(PROJECT, running_fn=lambda: True, connect_fn=lambda: kc) == "ipc"


def test_status_other_when_different_project():
    kc = FakeKiCad(docs={k.DOCTYPE_PCB: [doc_for("/elsewhere/x.kicad_pro")]})
    assert k.status(PROJECT, running_fn=lambda: True, connect_fn=lambda: kc) == "other"


def test_status_other_when_api_does_not_answer():
    def boom():
        raise ConnectionError("no socket")

    assert k.status(PROJECT, running_fn=lambda: True, connect_fn=boom) == "other"
    kc = FakeKiCad(ping_ok=False)
    assert k.status(PROJECT, running_fn=lambda: True, connect_fn=lambda: kc) == "other"


# ------------------------------------------------------------- set-fields

def rows_r13():
    return [("R13", "IPC_TEST", "1"), ("R13", "Value", "2k")]


def test_set_fields_one_commit_no_save():
    existing = field("IPC_TEST", "0")
    r13 = sym("R13", "id-r13", user=[existing])
    r14 = sym("R14", "id-r14")
    s = FakeSch([r13, r14])
    diff = k.set_fields(FakeKiCad(), rows_r13(), open_sch=lambda _k: s)
    assert s.calls.count("begin_commit") == 1
    assert s.calls.count("push_commit") == 1
    assert s.calls.index("begin_commit") < s.calls.index("update_items") < s.calls.index("push_commit")
    assert not {"save", "save_as", "revert", "drop_commit"} & set(s.calls)
    assert existing.text.value == "1"
    assert r13.value_field.text.value == "2k"
    assert r14.value_field.text.value == "1k"
    assert diff == ["R13.IPC_TEST: '0' -> '1'", "R13.Value: '1k' -> '2k'"]


def test_set_fields_dry_run_changes_nothing():
    r13 = sym("R13", "id-r13", user=[field("IPC_TEST", "0")])
    s = FakeSch([r13])
    diff = k.set_fields(FakeKiCad(), rows_r13(), dry_run=True, open_sch=lambda _k: s)
    assert s.calls == []
    assert r13.user_fields[0].text.value == "0"
    assert r13.value_field.text.value == "1k"
    assert len(diff) == 2


def test_set_fields_unknown_ref_commits_nothing():
    s = FakeSch([sym("R13", "id-r13")])
    with pytest.raises(k.IpcError, match="R99"):
        k.set_fields(FakeKiCad(), [("R99", "Value", "1")], open_sch=lambda _k: s)
    assert s.calls == []


def test_set_fields_drops_commit_on_failure():
    s = FakeSch([sym("R13", "id-r13")])

    def bad(items):
        s.calls.append("update_items")
        raise RuntimeError("rejected")

    s.update_items = bad
    with pytest.raises(RuntimeError):
        k.set_fields(FakeKiCad(), [("R13", "Value", "2k")], open_sch=lambda _k: s)
    assert "drop_commit" in s.calls and "push_commit" not in s.calls


def test_read_csv(tmp_path):
    f = tmp_path / "f.csv"
    f.write_text("ref,field,value\nR13,IPC_TEST,1\n")
    assert k.read_csv(f) == [("R13", "IPC_TEST", "1")]
    g = tmp_path / "g.csv"
    with open(g, "w", newline="") as fh:
        csv.writer(fh).writerows([["ref", "name"], ["R13", "x"]])
    with pytest.raises(k.IpcError):
        k.read_csv(g)


# -------------------------------------------------------------------- show

def test_show_maps_refs_and_nets_to_item_ids():
    fps = [sym("U30", "fp-u30"), sym("R1", "fp-r1")]
    nets = [NS(name="/ADF_DATA"), NS(name="GND")]
    items = {"/ADF_DATA": [NS(id=NS(value="trk1")), NS(id=NS(value="trk2"))], "GND": []}
    board = FakeBoard(fps, nets, items)
    s = FakeSch([sym("U30", "sy-u30"), sym("R1", "sy-r1")],
                labels=[NS(text=text("/ADF_DATA"), id=NS(value="lab1")),
                        NS(text=text("GND"), id=NS(value="lab2"))])
    res = k.show(FakeKiCad(), ["U30"], ["/ADF_DATA", "NOPE"],
                 open_pcb=lambda _k: board, open_sch=lambda _k: s)
    assert res["pcb"] == {"U30": ["fp-u30"], "/ADF_DATA": ["trk1", "trk2"]}
    assert res["sch"] == {"U30": ["sy-u30"], "/ADF_DATA": ["lab1"]}
    assert len(board.selection) == 3 and len(s.selection) == 2
    assert not {"save", "save_as", "revert", "begin_commit"} & set(board.calls + s.calls)


def test_show_pcb_only_skips_schematic():
    board = FakeBoard([sym("U30", "fp-u30")], [], {})

    def no_sch(_k):
        pytest.fail("schematic must not be opened")

    res = k.show(FakeKiCad(), ["U30"], [], sch=False, open_pcb=lambda _k: board, open_sch=no_sch)
    assert list(res) == ["pcb"]


# ---------------------------------------------------------- version mismatch

@pytest.mark.parametrize("kicad,api", [((10, 0, 7), (10, 0, 6)), ((10, 1, 0), (10, 0, 6)),
                                       ((9, 0, 5), (10, 0, 6)), ((11, 0, 0), (10, 0, 6))])
def test_version_mismatch_refused(kicad, api):
    kc = FakeKiCad(kicad=kicad, api=api)
    s = FakeSch([sym("R13", "id")])
    with pytest.raises(k.VersionMismatch, match="refusing"):
        k.set_fields(kc, [("R13", "Value", "1")], open_sch=lambda _k: s)
    with pytest.raises(k.VersionMismatch):
        k.show(kc, ["R13"], open_pcb=lambda _k: pytest.fail("opened"),
               open_sch=lambda _k: pytest.fail("opened"))
    assert s.calls == []


def test_version_accepts_older_patch():
    k.check_version(FakeKiCad(kicad=(10, 0, 5), api=(10, 0, 6)))
