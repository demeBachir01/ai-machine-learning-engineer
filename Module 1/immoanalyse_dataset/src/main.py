"""Point d'entrée unique : `python -m src.main` exécute tout le pipeline (phases 3 à 6) puis les contrôles (phase 8).

Options : --date-reference AAAA-MM-JJ (reproductibilité), --excel (export Excel facultatif).
Code de retour : 0 si tous les contrôles passent, 1 sinon.
"""
import argparse
import datetime as dt

import pandas as pd

from config import settings
from src.pipeline import executer
from src.processing.export import ecrire_excel
from src.verification import verifier_tout


def _excel(res) -> None:
    rep, proc = settings.REPORTS_DIR, settings.PROCESSED_DIR
    lire = lambda p: pd.read_csv(p, encoding=settings.ENCODAGE_CSV)
    feuilles = {"biens_dedupliques": lire(proc / "biens_dedupliques.csv"),
                "quarantaine": lire(settings.QUARANTINE_DIR / "quarantaine.csv"),
                "quality_summary": lire(rep / "quality_summary.csv"),
                "ventes_par_type": lire(rep / "analyse_ventes_par_type_bien.csv"),
                "ventes_par_ville": lire(rep / "analyse_ventes_par_ville.csv"),
                "locations_par_type": lire(rep / "analyse_locations_par_type_bien.csv")}
    ecrire_excel(rep / "immo_analyse.xlsx", feuilles)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Pipeline ImmoAnalyse : chargement, nettoyage, validation, doublons, "
                                                 "qualité, analyse")
    parser.add_argument("--date-reference", type=dt.date.fromisoformat, default=None,
                        help="date d'exécution pour la règle 'date non future' (défaut : aujourd'hui)")
    parser.add_argument("--excel", action="store_true", help="écrit aussi reports/immo_analyse.xlsx (facultatif)")
    args = parser.parse_args(argv)

    res = executer(reference=args.date_reference)
    if args.excel:
        _excel(res)
    b, q = res.bilan, res.qualite["statuts_finaux"]
    print(f"Date de référence : {b['date_reference']}")
    print(f"Reçus : {b['total_recus']} | doublons exacts écartés : {b['doublons_exacts_ecartes']} "
          f"({b['taux_doublons_exacts_pct']} %) | évalués : {b['total_evalues']}")
    print(f"  entièrement conformes : {q['entierement_conformes']} ({q['taux_entierement_conformes_pct']} % des évalués)")
    print(f"  conservés avec avertissement : {q['conserves_avec_avertissement']}")
    print(f"  en quarantaine : {q['quarantaine']} ({q['taux_quarantaine_pct']} %)")
    print(f"  corrigés : {q['corriges']} | valeurs inférées : {q['avec_valeur_inferee']}")
    r = b["rapprochement"]
    print(f"Rapprochement : {r['biens_uniques_apres_rapprochement']} biens uniques, "
          f"{r['paires_doublon_probable']} paires de doublons probables, {r['paires_conflit']} conflits")
    print("\nContrôles :")
    controles = verifier_tout(b)
    for nom, ok, detail in controles:
        print(f"  [{'OK' if ok else 'ÉCHEC'}] {nom}" + (f" — {detail}" if detail and not ok else ""))
    print(f"\nSorties : {settings.PROCESSED_DIR}, {settings.QUARANTINE_DIR}, {settings.REPORTS_DIR}")
    return 0 if all(ok for _, ok, _ in controles) else 1


if __name__ == "__main__":
    raise SystemExit(main())
