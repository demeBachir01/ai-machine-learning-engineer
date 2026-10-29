"""Indicateurs de qualité (phase 5, cahier §7). Tous les dénominateurs sont écrits à côté des taux.

Définitions
-----------
- Reçus      : toutes les lignes lues dans les 5 sources.
- Évalués    : reçus moins les doublons exacts écartés (ils ne sont ni bons ni mauvais, juste répétés).
- Statut final (UNE seule catégorie par évalué) : quarantaine | conservé avec avertissement | entièrement conforme.
- Taux global de conformité = entièrement conformes / évalués. Aucun enregistrement n'est compté deux fois.
- Taux de conformité d'une règle = conformes / évaluables ; les non évaluables sont comptés à part.
- « Corrigés » et « valeurs inférées » sont des drapeaux transversaux : ils ne s'additionnent pas aux statuts finaux.
"""
from collections import Counter
from typing import Dict, List

from src.validation.moteur import (AVERTISSEMENT, CONFORME, QUARANTAINE, DecisionBien, synthese_par_regle)

AVERTISSEMENT_PRIX_DEMANDE = ("Les données sont synthétiques et les prix de vente sont des prix demandés (annonces), "
                              "pas des prix de transaction conclue : ils ne servent pas à estimer le marché.")


def _pct(n: int, d: int):
    return round(100 * n / d, 2) if d else None


def _statuts(decisions: List[DecisionBien]) -> dict:
    c = Counter(d.statut_final for d in decisions)
    n = len(decisions)
    return {"evalues": n, "quarantaine": c[QUARANTAINE], "conserves_avec_avertissement": c[AVERTISSEMENT],
            "entierement_conformes": c[CONFORME],
            "taux_entierement_conformes_pct": _pct(c[CONFORME], n),
            "taux_quarantaine_pct": _pct(c[QUARANTAINE], n),
            "corriges": sum(1 for d in decisions if d.bien.est_corrige),
            "avec_valeur_inferee": sum(1 for d in decisions if d.bien.est_infere),
            "controle_somme_ok": c[QUARANTAINE] + c[AVERTISSEMENT] + c[CONFORME] == n}


def _manquants(inventaire: dict) -> dict:
    """Manquants par colonne sur les valeurs REÇUES. Une colonne que la source ne fournit pas n'est pas « manquante » :
    elle est comptée à part et sort du dénominateur."""
    colonnes: Dict[str, dict] = {}
    for nom, s in inventaire["sources"].items():
        for col, n in s["valeurs_manquantes"].items():
            c = colonnes.setdefault(col, {"manquantes": 0, "denominateur": 0, "sources_concernees": [],
                                          "sources_sans_la_colonne": []})
            c["manquantes"] += n
            c["denominateur"] += s["lignes"]
            c["sources_concernees"].append(nom)
        for col in s["colonnes_absentes_de_la_source"]:
            colonnes.setdefault(col, {"manquantes": 0, "denominateur": 0, "sources_concernees": [],
                                      "sources_sans_la_colonne": []})["sources_sans_la_colonne"].append(nom)
    for c in colonnes.values():
        c["taux_pct"] = _pct(c["manquantes"], c["denominateur"])
    return colonnes


def _erreurs_conversion(decisions: List[DecisionBien]) -> dict:
    par_champ: Dict[str, dict] = {}
    for d in decisions:
        for champ, motif in d.bien.erreurs_conversion.items():
            e = par_champ.setdefault(champ, {"erreurs": 0, "par_motif": Counter(), "par_source": Counter()})
            e["erreurs"] += 1
            e["par_motif"][motif.split(":")[0]] += 1
            e["par_source"][d.bien.source] += 1
    return {c: {"erreurs": e["erreurs"], "denominateur": len(decisions), "par_motif": dict(e["par_motif"]),
                "par_source": dict(e["par_source"])} for c, e in sorted(par_champ.items())}


def _motifs(decisions: List[DecisionBien], quarantaine: bool) -> dict:
    c = Counter()
    for d in decisions:
        for m in (d.motifs_quarantaine if quarantaine else d.motifs_avertissement):
            c[m.split(" [")[0]] += 1
    return dict(c.most_common())


def rapport_qualite(decisions: List[DecisionBien], inventaire: dict, doublons_exacts: List[dict],
                    rapprochement: dict, reference) -> dict:
    recus = inventaire["total_recus"]
    ecartes = len(doublons_exacts)
    sources = list(inventaire["sources"])
    return {
        "date_reference": reference.isoformat(),
        "avertissement_donnees": AVERTISSEMENT_PRIX_DEMANDE,
        "definitions": {
            "evalues": "reçus - doublons exacts écartés",
            "statut_final": "un seul par évalué : quarantaine | conserve_avec_avertissement | conforme",
            "taux_global_conformite": "entièrement conformes / évalués (jamais de double comptage)",
            "taux_regle": "conformes / évaluables ; les non évaluables sont comptés à part, jamais conformes par défaut",
            "corriges": "valeur reçue modifiée de façon fiable (drapeau transversal, non exclusif)",
            "inferes": "valeur absente de la source, déduite (drapeau transversal, non exclusif)",
            "motifs": "un enregistrement peut cumuler plusieurs motifs : la somme des motifs dépasse le nombre d'enregistrements",
        },
        "volumes": {"total_recus": recus, "doublons_exacts": ecartes,
                    "taux_doublons_exacts_pct": _pct(ecartes, recus), "denominateur_taux_doublons": recus,
                    "total_evalues": len(decisions),
                    "ventes_evaluees": sum(1 for d in decisions if d.bien.type_transaction == "vente"),
                    "locations_evaluees": sum(1 for d in decisions if d.bien.type_transaction == "location"),
                    "transaction_indeterminee": sum(1 for d in decisions if d.bien.type_transaction is None)},
        "statuts_finaux": _statuts(decisions),
        "statuts_par_source": {s: _statuts([d for d in decisions if d.bien.source == s]) for s in sources},
        "valeurs_manquantes_par_colonne": _manquants(inventaire),
        "erreurs_conversion_par_champ": _erreurs_conversion(decisions),
        "regles": synthese_par_regle(decisions),
        "motifs_quarantaine": _motifs(decisions, True),
        "motifs_avertissement": _motifs(decisions, False),
        "rapprochement": rapprochement,
    }


def rapport_vers_tableau(rapport: dict) -> List[dict]:
    """Vue à plat pour quality_summary.csv : section, source, indicateur, détail, valeur, dénominateur, taux_pct."""
    L = []

    def ajouter(section, indicateur, valeur, detail="", source="toutes", den=None, taux=None):
        L.append({"section": section, "source": source, "indicateur": indicateur, "detail": detail,
                  "valeur": valeur, "denominateur": den, "taux_pct": taux})

    v = rapport["volumes"]
    ajouter("volumes", "total_recus", v["total_recus"])
    ajouter("volumes", "doublons_exacts", v["doublons_exacts"], den=v["total_recus"], taux=v["taux_doublons_exacts_pct"])
    ajouter("volumes", "total_evalues", v["total_evalues"], "reçus - doublons exacts")
    for src, s in [("toutes", rapport["statuts_finaux"]), *rapport["statuts_par_source"].items()]:
        n = s["evalues"]
        for cle in ("quarantaine", "conserves_avec_avertissement", "entierement_conformes"):
            ajouter("statuts_finaux", cle, s[cle], source=src, den=n, taux=_pct(s[cle], n))
        ajouter("statuts_finaux", "corriges", s["corriges"], "drapeau transversal", src, n, _pct(s["corriges"], n))
        ajouter("statuts_finaux", "avec_valeur_inferee", s["avec_valeur_inferee"], "drapeau transversal", src, n,
                _pct(s["avec_valeur_inferee"], n))
    for col, m in rapport["valeurs_manquantes_par_colonne"].items():
        if m["denominateur"]:
            ajouter("valeurs_manquantes", col, m["manquantes"], "sources: " + ",".join(m["sources_concernees"]),
                    den=m["denominateur"], taux=m["taux_pct"])
        if m["sources_sans_la_colonne"]:
            ajouter("colonne_non_fournie", col, len(m["sources_sans_la_colonne"]), ",".join(m["sources_sans_la_colonne"]))
    for champ, e in rapport["erreurs_conversion_par_champ"].items():
        ajouter("erreurs_conversion", champ, e["erreurs"], str(e["par_motif"]), den=e["denominateur"],
                taux=_pct(e["erreurs"], e["denominateur"]))
    for r in rapport["regles"]:
        ajouter("regles", r["regle"], r["conformes"], f"action={r['action']}; non_conformes={r['non_conformes']}; "
                f"non_evaluables={r['non_evaluables']}", den=r["evaluables"], taux=r["taux_conformite"])
    for m, n in rapport["motifs_quarantaine"].items():
        ajouter("motifs_quarantaine", m, n)
    for m, n in rapport["motifs_avertissement"].items():
        ajouter("motifs_avertissement", m, n)
    for k, n in rapport["rapprochement"].items():
        ajouter("rapprochement", k, n)
    return L
