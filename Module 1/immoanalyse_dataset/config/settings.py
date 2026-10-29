"""Configuration centrale : aucun seuil ni mapping ne doit être codé en dur ailleurs."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
REF_DIR = ROOT / "data" / "referentiels"
PROCESSED_DIR = ROOT / "data" / "processed"
QUARANTINE_DIR = ROOT / "data" / "quarantine"
REPORTS_DIR = ROOT / "reports"

# --- Valeurs autorisées (cahier §6.1) ---
TYPES_TRANSACTION = {"vente", "location"}
PERIODICITES = {"mensuel", "trimestriel", "semestriel", "annuel"}
TYPES_BIEN = {"Appartement", "Studio", "Chambre", "Villa", "Maison", "Terrain", "Local commercial"}

# --- Seuils d'atypie globaux (regles_metier.md) : AVERTISSEMENT ---
SURFACE_ATYPIQUE_MIN = 5            # m²
SURFACE_ATYPIQUE_MAX = 2_000        # m²
PRIX_ATYPIQUE_MIN = 100_000         # FCFA
PRIX_ATYPIQUE_MAX = 2_000_000_000   # FCFA

# --- Loyers, pièces (cahier §6.2) : AVERTISSEMENT ---
LOYER_MIN_MENSUEL = 25_000
LOYER_MAX_MENSUEL = 5_000_000
MAX_CHAMBRES_APPART_STUDIO = 10
SDB_MARGE_SUR_CHAMBRES = 2
DIVISEUR_PERIODICITE = {"mensuel": 1, "trimestriel": 3, "semestriel": 6, "annuel": 12}

# --- Inférence du type de transaction pour l'agence (absent de la source) ---
# Constat : tous les montants < 2 M sont "Loué"/"Disponible" ; tous les >= 2 M sont "Vendu"/"En vente".
SEUIL_LOYER_VS_PRIX = 2_000_000

# --- Fourchettes indicatives par type (referentiel_categories.csv) : AVERTISSEMENT ---
#                      prix_min     prix_max    surf_min surf_max
FOURCHETTES = {
    "Appartement":      (25_000_000, 120_000_000,  45,  180),
    "Studio":           (12_000_000,  45_000_000,  20,   60),
    "Chambre":          ( 5_000_000,  18_000_000,  10,   30),
    "Villa":            (80_000_000, 450_000_000, 120,  450),
    "Maison":           (35_000_000, 180_000_000,  60,  250),
    "Terrain":          ( 8_000_000,  90_000_000,  80, 1500),
    "Local commercial": (30_000_000, 200_000_000,  40,  300),
}

# --- Synonymes (clé = texte sans accents, en minuscules) ---
SYNONYMES_TYPE_BIEN = {
    "appart": "Appartement", "appartement": "Appartement", "appt": "Appartement",
    "studio": "Studio",
    "chambre": "Chambre", "chambre simple": "Chambre",
    "villa": "Villa",
    "maison": "Maison",
    "terrain": "Terrain", "terrains": "Terrain",
    "local": "Local commercial", "local commercial": "Local commercial",
    "bureau": "Local commercial", "magasin": "Local commercial",
}
SYNONYMES_TRANSACTION = {
    "vente": "vente", "a vendre": "vente", "vendre": "vente",
    "location": "location", "a louer": "location", "louer": "location",
}
SYNONYMES_PERIODICITE = {
    "mensuel": "mensuel", "mens.": "mensuel", "mens": "mensuel", "mois": "mensuel",
    "/mois": "mensuel", "par mois": "mensuel", "fcfa/mois": "mensuel",
    "trimestriel": "trimestriel", "/trimestre": "trimestriel", "par trimestre": "trimestriel",
    "semestriel": "semestriel", "/semestre": "semestriel", "par semestre": "semestriel",
    "annuel": "annuel", "/an": "annuel", "par an": "annuel", "fcfa/an": "annuel",
}

# Alias de villes (clé sans accents). Aucun alias n'a été trouvé dans les 5 sources réelles.
ALIAS_VILLE = {"dkr": "Dakar"}

# --- Convention de lecture des dates à barres, PAR SOURCE ---
# Preuve : dans agence, particuliers et historique, le 1er nombre dépasse 12 (181/269/127 cas)
# et le 2e ne le dépasse jamais -> JJ/MM/AAAA. Les dates ISO ne dépendent pas de la convention.
CONVENTION_DATE = {
    "plateforme": "JJ/MM", "agence": "JJ/MM", "particuliers": "JJ/MM",
    "notaires": "JJ/MM", "historique": "JJ/MM",
}

# Les coordonnées du référentiel sont identiques pour toutes les villes d'une région : inutilisables.
USE_COORDONNEES_REFERENTIEL = False

# --- Schéma cible : clés attendues d'un enregistrement brut APRÈS renommage des colonnes (phase 2/3) ---
# 'montant' = prix OU loyer : on ne sait lequel qu'une fois le type de transaction connu.
COLONNES_BRUTES_CIBLE = (
    "id_local", "type_transaction", "type_bien", "region", "ville", "quartier", "montant",
    "periodicite", "surface", "pieces", "chambres", "salles_bain",
    "date_collecte", "date_mise_a_jour", "statut",
)

# Types de bien pour lesquels le nombre de chambres est contrôlé (cahier §6.2)
TYPES_BIEN_CHAMBRES_CONTROLEES = ("Appartement", "Studio")
