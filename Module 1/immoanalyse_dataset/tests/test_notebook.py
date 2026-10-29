"""Le notebook est un JSON valide, son code compile et il ne dépend d'aucun chemin absolu."""
import ast
import json

from config import settings

NB = settings.ROOT / "notebooks" / "01_exploration.ipynb"


def charger():
    return json.loads(NB.read_text(encoding="utf-8"))


def test_structure_nbformat():
    nb = charger()
    assert nb["nbformat"] == 4 and nb["cells"]
    types = {c["cell_type"] for c in nb["cells"]}
    assert types == {"markdown", "code"}


def test_le_code_compile_et_pas_de_chemin_absolu():
    for c in charger()["cells"]:
        if c["cell_type"] == "code":
            src = "".join(c["source"])
            ast.parse(src)
            assert "/home/" not in src and "/tmp/" not in src and "C:\\" not in src


def test_sections_demandees_et_rappel_donnees_synthetiques():
    texte = "\n".join("".join(c["source"]) for c in charger()["cells"] if c["cell_type"] == "markdown")
    for titre in ("## 1.", "## 2.", "## 3.", "## 4.", "## 5."):
        assert titre in texte
    assert "synthétiques" in texte and "prix demandés" in texte and "Limites" in texte


def test_les_sorties_sont_enregistrees_sans_erreur():
    for c in charger()["cells"]:
        if c["cell_type"] == "code":
            assert c["outputs"] is not None
            assert not any(o["output_type"] == "error" for o in c["outputs"])
