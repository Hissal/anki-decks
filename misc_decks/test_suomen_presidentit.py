# -*- coding: utf-8 -*-
"""Unit tests for the Suomen Presidentit builder. Run from misc_decks/:

    python -m pytest test_suomen_presidentit.py -q
"""

import json
import pathlib

import build_suomen_presidentit as b

_HERE = pathlib.Path(__file__).resolve().parent


def _src_president_model():
    deck = json.loads((_HERE / "Suomen_presidentit" / "deck.source.json")
                      .read_text(encoding="utf-8"))
    return deck["note_models"][0]


# --- normalize_years -------------------------------------------------------- #
def test_normalize_years_plain_range():
    assert b.normalize_years("25.7. 1919 - 2.3.1 1925") == "1919–1925"


def test_normalize_years_strips_wikipedia_links():
    raw = ('<a href="https://fi.wikipedia.org/wiki/2._maaliskuuta">2.3.</a>'
           '<a href="https://fi.wikipedia.org/wiki/1925">1925</a>&nbsp;–&nbsp;'
           '<a href="https://fi.wikipedia.org/wiki/1931">1931</a>')
    assert b.normalize_years(raw) == "1925–1931"


def test_normalize_years_died_in_office_marker():
    raw = ('<a href="x">1.3.</a><a href="y">1937</a>&nbsp;–&nbsp;'
           '<a href="z">19.12.</a><a href="w">1940</a>†')
    assert b.normalize_years(raw) == "1937–1940 †"


def test_normalize_years_current_term():
    assert b.normalize_years("1.3.2024 -&gt;") == "2024–"


# --- normalize_info / canon_party ------------------------------------------- #
def test_normalize_info_strips_table_wrapper():
    raw = "<table><tbody><tr><td><br>Ståhlbergin kausi alkoi myöhemmin.</td></tr></tbody></table>"
    assert b.normalize_info(raw) == "Ståhlbergin kausi alkoi myöhemmin."


def test_normalize_info_strips_citation_sup():
    raw = ('Koiviston kaudella valtaa vähennettiin.'
           '<sup><a href="x">[4]</a></sup>&nbsp;Päätös ei koskenut häntä.')
    assert b.normalize_info(raw) == "Koiviston kaudella valtaa vähennettiin. Päätös ei koskenut häntä."


def test_canon_party_maps_variants():
    assert b.canon_party("Kokoomuspuolue") == "Kokoomus"
    assert b.canon_party("Kokoomus") == "Kokoomus"
    assert b.canon_party("Sosiaalidemokraatti") == "Sosiaalidemokraatit (SDP)"
    assert b.canon_party("Sitoutumaton") == "Sitoutumaton"


# --- compute_neighbors ------------------------------------------------------ #
def test_compute_neighbors():
    rows = [(1, "K. J. Ståhlberg"), (2, "Lauri Kristian Relander"), (3, "P.E. Svinhufvud")]
    pred, succ = b.compute_neighbors(rows)
    assert pred[1] == ""
    assert succ[1] == "Lauri Kristian Relander (2.)"
    assert pred[2] == "K. J. Ståhlberg (1.)"
    assert succ[3] == ""


# --- per-president model ---------------------------------------------------- #
def test_president_template_order_and_req():
    model = b.build_president_model(_src_president_model())
    names = [t["name"] for t in model["tmpls"]]
    assert names == [
        "Image → Name", "KnownFor → Name", "Nickname → Name", "Years → Name",
        "Ordinal → Name", "Name → Ordinal", "Name → Party", "Name → KnownFor",
        "Name → Profession", "Name → Birthplace", "Name → Predecessor",
        "Name → Successor", "Name → Years", "Name → Life",
    ]
    assert [t["ord"] for t in model["tmpls"]] == list(range(14))
    assert [r[0] for r in model["req"]] == list(range(14))
    fnames = [f["name"] for f in model["flds"]]
    assert fnames[:6] == ["Ordinal", "Name", "Years", "Image", "Party", "Info"]
    assert set(fnames[6:]) == {"Life", "Profession", "Birthplace", "KnownFor",
                               "Nickname", "Link", "Predecessor", "Successor"}


def test_president_req_field_indexes():
    model = b.build_president_model(_src_president_model())
    idx = {f["name"]: i for i, f in enumerate(model["flds"])}
    req_by_name = {model["tmpls"][r[0]]["name"]: (r[1], r[2]) for r in model["req"]}
    assert req_by_name["Image → Name"] == ("any", [idx["Image"]])
    assert req_by_name["Name → Party"] == ("all", [idx["Party"]])
    assert req_by_name["Name → Successor"] == ("all", [idx["Successor"]])


# --- aggregates ------------------------------------------------------------- #
def test_party_rosters_partition_all_13():
    notes = b._president_rows_for_test()
    rosters = b.build_party_rosters(notes)
    assert len(rosters) == 5
    joined = " ".join(ans for _f, ans in rosters)
    for _o, name, _p in notes:
        assert joined.count(name) == 1          # each president in exactly one roster
    assert sum(ans.count("(") for _f, ans in rosters) == 13


def test_recite_note_lists_all_13():
    notes = b._president_rows_for_test()
    front, back = b.build_recite_note(notes)
    assert "järjestyksessä" in front
    for _o, name, _p in notes:
        assert name in back
    assert "<details>" in back


def test_trivia_count_matches_data():
    assert len(b.build_trivia_notes()) == len(b.TRIVIA)


def test_guid_for_is_deterministic():
    assert b.guid_for("abc") == b.guid_for("abc")
    assert b.guid_for("abc") != b.guid_for("abd")
