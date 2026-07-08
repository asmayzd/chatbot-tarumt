import os
import sys
import configparser
from pathlib import Path


def check(label, ok, detail=""):
    mark = "OK  " if ok else "FAIL"
    print(f"[{mark}] {label}")
    if detail:
        print(f"       -> {detail}")
    return ok


print("=" * 60)
print("DIAGNOSTIC GEMINI / SQL AGENT")
print("=" * 60)

# 1. Where are we running from?
cwd = Path.cwd()
print(f"\nDossier courant : {cwd}\n")

# 2. config.ini present here?
config_path = Path("config.ini")
step2 = check(
    "config.ini trouve dans le dossier courant",
    config_path.exists(),
    "Place config.ini a la racine et lance streamlit DEPUIS la racine."
    if not config_path.exists() else "",
)

# 3. config.ini well-formed with the key?
key_value = None
if step2:
    config = configparser.ConfigParser()
    config.read(config_path)

    has_section = "API_KEYS" in config
    check(
        "Section [API_KEYS] presente",
        has_section,
        f"Sections trouvees : {config.sections()}" if not has_section else "",
    )

    if has_section:
        has_key = "GEMINI_API_KEY" in config["API_KEYS"]
        check(
            "Cle GEMINI_API_KEY presente",
            has_key,
            f"Cles trouvees : {list(config['API_KEYS'].keys())}" if not has_key else "",
        )

        if has_key:
            key_value = config["API_KEYS"]["GEMINI_API_KEY"].strip()
            looks_ok = len(key_value) > 20 and not key_value.startswith(("'", '"'))
            check(
                "La cle a l'air valide (longueur, pas de guillemets)",
                looks_ok,
                f"Valeur lue : {repr(key_value[:8])}... (longueur {len(key_value)})",
            )

# 4. Library installed?
try:
    from google import genai
    lib_ok = True
except ImportError as exc:
    lib_ok = False
    check("Librairie google-genai installee", False, f"{exc}  ->  pip install google-genai")

if lib_ok:
    check("Librairie google-genai installee", True)

# 5. Client init + tiny real call
if lib_ok and key_value:
    os.environ["GEMINI_API_KEY"] = key_value
    try:
        client = genai.Client()
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents="Reply with the single word: OK",
        )
        check("Appel Gemini reussi", True, f"Reponse : {response.text.strip()!r}")
    except Exception as exc:
        check(
            "Appel Gemini reussi",
            False,
            f"{type(exc).__name__}: {exc}",
        )

print("\n" + "=" * 60)
print("Si tout est [OK] ci-dessus, l'agent s'activera dans l'app.")
print("=" * 60)
