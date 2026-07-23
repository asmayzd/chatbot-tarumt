import os
from pypdf import PdfReader
from google import genai


class RAGAgent:
    """
    RAG Agent servant à lire les documents PDF selon le rôle (Client vs Interne).
    """

    def __init__(self, base_docs_dir: str = "docs", model: str = "gemini-3.1-flash-lite"):
        self.base_docs_dir = os.path.abspath(base_docs_dir)
        self.model = model
        self.client = None

    def init_gemini(self):
        """Initialise le client Gemini."""
        if self.client is None:
            self.client = genai.Client()
        return self

    def _extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extrait le texte d'un fichier PDF."""
        text = ""
        try:
            reader = PdfReader(pdf_path)
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"
        except Exception as e:
            print(f"⚠️ Erreur de lecture pour {pdf_path}: {e}")
        return text

    def load_context(self, role: str = "user") -> str:
        """
        Charge les PDF du dossier 'client' pour les rôles 'user'/'analyst',
        et inclut aussi 'interne' si le rôle est 'admin'.
        """
        context_text = ""
        dirs_to_read = ["client"]
        if role == "admin":
            dirs_to_read.append("interne")

        for folder in dirs_to_read:
            target_dir = os.path.join(self.base_docs_dir, folder)
            if not os.path.exists(target_dir):
                continue

            for filename in os.listdir(target_dir):
                if filename.endswith(".pdf"):
                    filepath = os.path.join(target_dir, filename)
                    content = self._extract_text_from_pdf(filepath)
                    if content.strip():
                        context_text += f"\n--- DOCUMENT ({folder.upper()}): {filename} ---\n" + content

        return context_text.strip()

    def query(self, question: str, role: str = "user") -> dict:
        """Génère une réponse basée sur les PDF autorisés pour ce rôle."""
        self.init_gemini()
        context = self.load_context(role=role)

        if not context:
            return {
                "answer": "Aucun document d'entreprise pertinent n'est disponible.",
                "sources": []
            }

        prompt = f"""
You are the official Virtual Assistant for TARUMT Store.

CRITICAL LANGUAGE & SAFETY INSTRUCTIONS:
1. DETECT QUESTION LANGUAGE: Check the language of the USER QUESTION below. You MUST reply STRICTLY in that EXACT SAME LANGUAGE.
   - If the user asks in English, translate the extracted information and reply fully in English.
   - If the user asks in French, reply in French.
2. Answer the question ONLY using the CONTEXT provided below.
3. If the information is not present in the context, reply politely in the user's language (e.g., "I cannot find this information in the official documentation.").
4. Do NOT invent or hallucinate any facts.
5. FORMATTING: Do NOT use asterisks (*) or hash symbols (#). Return plain text only.

================ DOCUMENT CONTEXT ================
{context}
==================================================

USER QUESTION: "{question}"

YOUR RESPONSE (In the exact language of the USER QUESTION):
""".strip()

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt
            )
            clean_text = response.text.replace("*", "").replace("#", "").strip()
            return {"answer": clean_text}
        except Exception as e:
            return {"answer": f"Error consulting documents: {e}"}