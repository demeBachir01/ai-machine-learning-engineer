"""Orchestration des phases 3 et 4 : charger -> dédoublonner -> normaliser -> valider -> rapprocher -> exporter.

Chaque enregistrement reçu aboutit dans UNE seule catégorie finale :
  doublon exact écarté | quarantaine | conservé avec avertissement | entièrement conforme.
Contrôle : retenus + quarantaine + doublons exacts écartés = total reçu.
"""
import datetime as dt
import hashlib
from dataclasses import dataclass, field
from typing import List, Optional

import pandas as pd

from config import settings
from src.analysis import analyser, charger_biens, ecrire_analyse
from src.loaders import (TOUS_LES_CHARGEURS, charger_toutes_les_sources, dataframe_brut_unifie)
from src.loaders.inventaire import inventaire_anomalies, inventaire_vers_tableau
from src.processing import construire_bien
from src.processing.doublons import (fusionner_groupe, ordre_priorite, rapprocher, separer_doublons_exacts)
from src.processing.export import ecrire_csv, ecrire_json, ecrire_objet_json
from src.utils import construire_index_geo
from src.validation import (QUARANTAINE, DecisionBien, Validateur, rapport_qualite, rapport_vers_tableau,
                            synthese_globale)

CHAMPS_BRUTS_EXPORT = ("type_transaction", "type_bien", "region", "ville", "montant", "periodicite", "surface",
                       "chambres", "salles_bain", "date_collecte", "statut")


@dataclass
class ResultatPipeline:
    reference: dt.date
    brut: pd.DataFrame
    inventaire: dict
    doublons_exacts: List[dict]
    decisions: List[DecisionBien]                 # tous les enregistrements évalués (hors doublons exacts)
    retenus: List[DecisionBien] = field(default_factory=list)
    quarantaine: List[DecisionBien] = field(default_factory=list)
    rapprochement: object = None
    dedupliques: List[dict] = field(default_factory=list)
    bilan: dict = field(default_factory=dict)
    qualite: dict = field(default_factory=dict)


def charger_referentiel_geo() -> dict:
    return construire_index_geo(pd.read_csv(settings.REF_DIR / "referentiel_geographique.csv"))


def empreinte_sources() -> dict:
    """SHA-256 des fichiers bruts (preuve que data/raw n'est pas modifié par le pipeline)."""
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(settings.RAW_DIR.glob("*"))
            if p.is_file()}


def executer(reference: Optional[dt.date] = None, ecrire: bool = True) -> ResultatPipeline:
    reference = reference or dt.date.today()
    avant = empreinte_sources()
    index_geo = charger_referentiel_geo()
    sources = charger_toutes_les_sources()                       # phase 3
    brut = dataframe_brut_unifie(sources)
    inventaire = inventaire_anomalies(sources, index_geo)

    # --- doublons exacts : écartés AVANT validation (1re occurrence conservée)
    doublons_exacts, biens = [], []
    for nom, (chargeur, enregistrements) in sources.items():
        uniques, doubles = separer_doublons_exacts(enregistrements)
        doublons_exacts += [{"source": nom, "fichier": chargeur.contexte.fichier, **d} for d in doubles]
        for e in uniques:                                         # phase 4.1 : normalisation
            biens.append(construire_bien(e, chargeur.contexte, index_geo))

    # --- phase 4.2 : validation par règles
    decisions = Validateur(reference=reference).valider_lot(biens)
    retenus = [d for d in decisions if d.statut_final != QUARANTAINE]
    quarantaine = [d for d in decisions if d.statut_final == QUARANTAINE]

    # --- phase 4.3 : rapprochement sur les seuls enregistrements retenus, par ordre de priorité des sources
    retenus.sort(key=lambda d: ordre_priorite(d.bien))
    rapp = rapprocher([d.bien for d in retenus])
    for pos, d in enumerate(retenus):
        d.bien.id_bien = rapp.id_bien[pos]
    dedupliques = _construire_dedupliques(retenus, rapp)

    res = ResultatPipeline(reference, brut, inventaire, doublons_exacts, decisions, retenus, quarantaine,
                           rapp, dedupliques)
    res.bilan = _bilan(res, sources, avant == empreinte_sources())
    res.qualite = rapport_qualite(res.decisions, res.inventaire, res.doublons_exacts, res.bilan["rapprochement"],
                                  reference)                                  # phase 5
    if ecrire:
        _exporter(res, sources)
    return res


# ------------------------------------------------------------------ construction des sorties
def _ligne_bien(d: DecisionBien, rapp=None, pos=None) -> dict:
    b = d.bien
    ligne = {"id_bien": b.id_bien, "source": b.source, "fichier": b.fichier, "ligne_origine": b.ligne_origine}
    ligne.update({k: v for k, v in b.vers_dict().items() if k not in ligne})
    ligne.pop("geo_coherent", None)
    ligne["prix_m2"] = b.prix_m2
    ligne["statut_validation"] = d.statut_final
    ligne["avertissements"] = " | ".join(d.motifs_avertissement)
    ligne["corrige"] = b.est_corrige
    ligne["valeur_inferee"] = b.est_infere
    if rapp is not None:
        ligne["statut_rapprochement"] = rapp.statut[pos]
    return ligne


def _construire_dedupliques(retenus: List[DecisionBien], rapp) -> List[dict]:
    """Une ligne par id_bien : le membre prioritaire, complété (et tracé) par ses doublons probables."""
    lignes = []
    ordre_statut = ("unique", "doublon_probable", "conflit")
    for id_bien, positions in rapp.groupes().items():
        pos_maitre = min(positions, key=lambda p: ordre_priorite(retenus[p].bien))
        maitre, completes, sources = fusionner_groupe([retenus[p].bien for p in positions])
        ligne = _ligne_bien(DecisionBien(maitre, retenus[pos_maitre].resultats), rapp, pos_maitre)
        ligne["statut_rapprochement"] = max((rapp.statut[p] for p in positions), key=ordre_statut.index)
        ligne["nb_enregistrements"] = len(positions)
        ligne["sources_membres"] = " | ".join(sources)
        ligne["champs_completes"] = " | ".join(completes)
        lignes.append(ligne)
    return lignes


def _journal(res: ResultatPipeline) -> List[dict]:
    lignes = []
    for d in res.decisions:
        b = d.bien
        base = {"source": b.source, "fichier": b.fichier, "ligne_origine": b.ligne_origine, "id_local": b.id_local,
                "statut_final": d.statut_final}
        for c in b.corrections:
            lignes.append({**base, "nature": "correction", "champ": c.champ, "ancienne_valeur": c.ancienne_valeur,
                           "nouvelle_valeur": c.nouvelle_valeur, "motif": c.motif})
        for champ, motif in b.inferences.items():
            lignes.append({**base, "nature": "inference", "champ": champ, "ancienne_valeur": None,
                           "nouvelle_valeur": getattr(b, champ), "motif": motif})
    return lignes


def _ligne_quarantaine(d: DecisionBien) -> dict:
    b = d.bien
    ligne = {"source": b.source, "fichier": b.fichier, "ligne_origine": b.ligne_origine, "id_local": b.id_local,
             "motifs_quarantaine": " | ".join(d.motifs_quarantaine),
             "motifs_avertissement": " | ".join(d.motifs_avertissement),
             "erreurs_conversion": " | ".join(f"{k}:{v}" for k, v in b.erreurs_conversion.items())}
    for champ in CHAMPS_BRUTS_EXPORT:
        ligne[f"brut_{champ}"] = b.valeurs_brutes.get(champ)
    return ligne


def _bilan(res: ResultatPipeline, sources: dict, sources_intactes: bool) -> dict:
    synthese = synthese_globale(res.decisions)
    recus = res.inventaire["total_recus"]
    ecartes = len(res.doublons_exacts)
    par_source = {}
    for nom in sources:
        ds = [d for d in res.decisions if d.bien.source == nom]
        par_source[nom] = {
            "recus": res.inventaire["sources"][nom]["lignes"],
            "doublons_exacts_ecartes": sum(1 for x in res.doublons_exacts if x["source"] == nom),
            "quarantaine": sum(1 for d in ds if d.statut_final == QUARANTAINE),
            "conserves_avec_avertissement": sum(1 for d in ds if d.statut_final == "conserve_avec_avertissement"),
            "entierement_conformes": sum(1 for d in ds if d.statut_final == "conforme"),
        }
    groupes = res.rapprochement.groupes()
    return {
        "date_reference": res.reference.isoformat(),
        "total_recus": recus,
        "doublons_exacts_ecartes": ecartes,
        "taux_doublons_exacts_pct": round(100 * ecartes / recus, 2) if recus else None,
        "total_evalues": len(res.decisions),
        "quarantaine": len(res.quarantaine),
        "retenus": len(res.retenus),
        "conserves_avec_avertissement": synthese["conserves_avec_avertissement"],
        "entierement_conformes": synthese["entierement_conformes"],
        "corriges": synthese["corriges"],
        "avec_valeur_inferee": synthese["avec_valeur_inferee"],
        "controle_total_ok": len(res.retenus) + len(res.quarantaine) + ecartes == recus,
        "rapprochement": {
            "non_rapprochables_attributs_manquants": res.rapprochement.non_rapprochables,
            "paires_doublon_probable": sum(1 for p in res.rapprochement.paires if p["lien"] == "doublon_probable"),
            "paires_conflit": sum(1 for p in res.rapprochement.paires if p["lien"] == "conflit"),
            "paires_montant_non_evaluable": res.rapprochement.paires_montant_non_evaluable,
            "biens_uniques_apres_rapprochement": len(groupes),
            "enregistrements_fusionnes_en_doublon": len(res.retenus) - len(groupes),
        },
        "par_source": par_source,
        "sources_intactes": sources_intactes,
    }


def _exporter(res: ResultatPipeline, sources: dict) -> None:
    proc, quar, rep = settings.PROCESSED_DIR, settings.QUARANTINE_DIR, settings.REPORTS_DIR
    brut = res.brut.where(res.brut.notna(), None).to_dict("records")
    ecrire_csv(brut, proc / "brut_unifie.csv")                                      # phase 3
    ecrire_objet_json(res.inventaire, rep / "inventaire_anomalies.json")
    inventaire_vers_tableau(res.inventaire).to_csv(rep / "inventaire_anomalies.csv", index=False,
                                                   encoding=settings.ENCODAGE_CSV)
    retenus = [_ligne_bien(d, res.rapprochement, i) for i, d in enumerate(res.retenus)]   # phase 4
    ecrire_csv(retenus, proc / "biens_retenus.csv")
    ecrire_json(retenus, proc / "biens_retenus.json")
    ecrire_csv(res.dedupliques, proc / "biens_dedupliques.csv")
    ecrire_json(res.dedupliques, proc / "biens_dedupliques.json")
    ecrire_csv(_journal(res), proc / "journal_corrections.csv",
               ["nature", "source", "fichier", "ligne_origine", "id_local", "champ", "ancienne_valeur",
                "nouvelle_valeur", "motif", "statut_final"])
    ecrire_csv(res.rapprochement.paires, proc / "rapprochements.csv")
    ecrire_csv(res.doublons_exacts, proc / "doublons_exacts_ecartes.csv")
    ecrire_csv([_ligne_quarantaine(d) for d in res.quarantaine], quar / "quarantaine.csv")
    ecrire_json([_ligne_quarantaine(d) for d in res.quarantaine], quar / "quarantaine.json")
    ecrire_objet_json(res.bilan, rep / "bilan_traitement.json")
    ecrire_objet_json(res.qualite, rep / "quality_report.json")                       # phase 5
    ecrire_csv(rapport_vers_tableau(res.qualite), rep / "quality_summary.csv",
               ["section", "source", "indicateur", "detail", "valeur", "denominateur", "taux_pct"])
    analyse = analyser(charger_biens(proc / "biens_dedupliques.csv"))                # phase 6 : lit les fichiers produits
    ecrire_analyse(analyse, rep)
