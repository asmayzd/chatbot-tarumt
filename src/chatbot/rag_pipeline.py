"""
Module Data Science / ML — Pipeline RAG (Retrieval-Augmented Generation) léger.

Approche : découpage des documents en passages -> vectorisation TF-IDF ->
recherche du passage le plus proche de la question (similarité cosinus).

On utilise scikit-learn (TF-IDF) plutôt que FAISS/ChromaDB pour rester léger
et sans dépendance lourde. Le contrat est identique : on pourrait remplacer
la couche de retrieval par une base vectorielle sans toucher au reste.

Contrat exposé :
    retrieve(question: str, k: int = 1) -> list[dict]
    answer_from_docs(question: str) -> dict
"""
import glob
import os
import re

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

DOCS_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "..", "data", "documents",
)


def _charger_passages():
    """Charge les documents et les découpe en passages (par section markdown)."""
    passages = []
    for path in glob.glob(os.path.join(DOCS_DIR, "*.md")):
        with open(path, encoding="utf-8") as f:
            contenu = f.read()
        source = os.path.basename(path)
        # découpage par titre de section (##)
        blocs = re.split(r"\n##\s+", contenu)
        for bloc in blocs:
            bloc = bloc.strip()
            if len(bloc) < 20:
                continue
            titre = bloc.split("\n", 1)[0].strip("# ").strip()
            passages.append({"source": source, "titre": titre, "texte": bloc})
    return passages


class RagIndex:
    """Index TF-IDF construit une seule fois puis réutilisé."""
    def __init__(self):
        self.passages = _charger_passages()
        self.vectorizer = TfidfVectorizer()
        corpus = [p["texte"] for p in self.passages] or [""]
        self.matrice = self.vectorizer.fit_transform(corpus)

    def retrieve(self, question: str, k: int = 1):
        if not self.passages:
            return []
        vec = self.vectorizer.transform([question])
        scores = cosine_similarity(vec, self.matrice)[0]
        ordre = scores.argsort()[::-1][:k]
        resultats = []
        for i in ordre:
            resultats.append({
                "source": self.passages[i]["source"],
                "titre": self.passages[i]["titre"],
                "texte": self.passages[i]["texte"],
                "score": round(float(scores[i]), 3),
            })
        return resultats


_INDEX = None

def _index():
    global _INDEX
    if _INDEX is None:
        _INDEX = RagIndex()
    return _INDEX


def retrieve(question: str, k: int = 1):
    return _index().retrieve(question, k)


def answer_from_docs(question: str) -> dict:
    """
    Renvoie une réponse fondée sur le meilleur passage documentaire.
    Contrat : {"answer", "source", "confidence"}
    """
    res = retrieve(question, k=1)
    if not res or res[0]["score"] < 0.05:
        return {"answer": "Je n'ai pas trouvé d'information sur ce point dans la "
                          "base documentaire.",
                "source": None, "confidence": 0.0}
    top = res[0]
    # on renvoie le corps de la section (sans le titre) comme réponse
    corps = top["texte"].split("\n", 1)[-1].strip()
    return {"answer": corps, "source": top["source"],
            "confidence": top["score"]}


if __name__ == "__main__":
    for q in ["Quels sont les délais de livraison ?",
              "Comment fonctionne un retour produit ?",
              "Quelle est la garantie sur l'électronique ?"]:
        r = answer_from_docs(q)
        print(f"Q: {q}\n-> ({r['confidence']}) {r['answer'][:90]}...\n")
