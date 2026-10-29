import datetime as dt
import pytest

from src.utils import parse_date, est_future

REF = dt.date(2026, 10, 29)


def test_iso():
    r = parse_date("2024-03-01")
    assert r.valeur == dt.date(2024, 3, 1) and r.statut == "ok"


def test_slash_jour_superieur_12_est_certain():
    r = parse_date("17/06/2019", convention=None)
    assert r.valeur == dt.date(2019, 6, 17) and r.statut == "corrige"


def test_slash_ambigu_sans_convention():
    r = parse_date("01/03/2024", convention=None)
    assert r.statut == "ambigu" and r.valeur is None


def test_slash_ambigu_avec_convention_documentee():
    r = parse_date("01/03/2024", convention="JJ/MM")
    assert r.valeur == dt.date(2024, 3, 1) and "convention_source" in r.motif
    assert parse_date("01/03/2024", convention="MM/JJ").valeur == dt.date(2024, 1, 3)


@pytest.mark.parametrize("brut", ["32/13/2024", "31/02/2024", "2024-02-30", "n'importe quoi"])
def test_dates_impossibles_ou_illisibles(brut):
    r = parse_date(brut)
    assert r.statut == "erreur" and r.valeur is None


def test_mois_en_lettres():
    assert parse_date("12 mars 2024").valeur == dt.date(2024, 3, 12)
    assert parse_date("1er février 2023").valeur == dt.date(2023, 2, 1)
    assert parse_date("5 décembre 2021").valeur == dt.date(2021, 12, 5)


def test_hier_relatif():
    assert parse_date("hier", reference=REF).valeur == dt.date(2026, 10, 28)
    assert parse_date("hier").statut == "ambigu"        # sans date de référence, on ne devine pas


def test_absente():
    assert parse_date(None).statut == "absent"


def test_date_future():
    assert est_future(dt.date(2027, 1, 1), REF) is True
    assert est_future(dt.date(2026, 10, 29), REF) is False      # cas limite : aujourd'hui n'est pas futur
    assert est_future(None, REF) is None                          # non évaluable
