from openai import OpenAI
import speech_recognition as sr
import edge_tts
import asyncio
import pygame
import os
import tempfile
import threading
import time
import re
import sys
import queue
from dotenv import load_dotenv

# Encodage console UTF-8 sous Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# ==============================
# CONFIG
# ==============================
load_dotenv(dotenv_path=".env", override=True)
API_KEY = os.environ.get("API_KEY")
BASE_URL = "https://api.groq.com/openai/v1"
MODEL = "llama-3.3-70b-versatile"
SEUIL_VOIX = 150  # Sensibilité micro hyper réactive

if not API_KEY:
    print("⚠️ ATTENTION : Aucune clé API_KEY trouvée dans le fichier .env !")

client = OpenAI(api_key=API_KEY or "DUMMY_KEY", base_url=BASE_URL)

SYSTEM_PROMPT = """Tu es PH.AI, mon IA a moi ton createur PHANUEL 


TA MÉTHODE DE RÉPONSE (toujours dans cet ordre) :
- Explication — claire et simple
- Exemple concret — contexte ivoirien si possible
- Le savais-tu ? — un fait de culture générale
- Conseil — une astuce pour progresser

TES RÈGLES :
- MEt dans tes reponse quelque mot anglais (combine avec le français) pour rendre la conversation plus naturelle(franc-anglais)
- Tu réponds TOUJOURS en franc-anglais
- Tes réponses vocales sont courtes et claires
- Tu encourages toujours à la fin"""


# ==============================
# ÉTAT GLOBAL
# ==============================
ia_parle = threading.Event()       # True quand l'IA parle
interrompu = threading.Event()     # True quand l'utilisateur coupe la parole
ecoute_active = threading.Event()  # True quand le micro écoute la prochaine question
saisie_queue = queue.Queue()       # Queue thread-safe (Clavier + Vocal)


# ==============================
# SURVEILLANCE DU MICRO (interruption pendant la parole de l'IA)
# ==============================
def surveiller_micro():
    """Écoute le micro pendant que l'IA parle et coupe la parole UNIQUEMENT si 'ATTEND' ou 'STOP' est dit."""
    recognizer = sr.Recognizer()
    recognizer.dynamic_energy_threshold = True
    MOTS_CLES_INTERRUPTION = ["attend", "attends", "attendez", "stop", "pause", "arret", "arrête", "arrete"]

    while True:
        if ia_parle.is_set():
            time.sleep(0.3)
            if not ia_parle.is_set():
                continue

            try:
                with sr.Microphone() as source:
                    recognizer.adjust_for_ambient_noise(source, duration=0.3)
                    while ia_parle.is_set() and not interrompu.is_set():
                        try:
                            audio = recognizer.listen(source, timeout=0.8, phrase_time_limit=2.0)
                            if ia_parle.is_set():
                                mots_dits = recognizer.recognize_google(audio, language="fr-FR").lower()
                                if any(kw in mots_dits for kw in MOTS_CLES_INTERRUPTION):
                                    pygame.mixer.music.stop()
                                    interrompu.set()
                                    print("\n🛑 [Mot-clé 'ATTEND' détecté ! PH.AI s'arrête]")
                                    break
                        except (sr.WaitTimeoutError, sr.UnknownValueError):
                            pass
                        except Exception:
                            break
            except Exception:
                time.sleep(0.2)
        else:
            time.sleep(0.1)


# ==============================
# ÉCOUTE VOCALE DES QUESTIONS (arrière-plan)
# ==============================
def thread_ecoute_vocale():
    """Écoute le microphone quand PH.AI attend une question."""
    recognizer = sr.Recognizer()
    recognizer.energy_threshold = SEUIL_VOIX
    recognizer.dynamic_energy_threshold = False

    while True:
        if ecoute_active.is_set() and not ia_parle.is_set():
            try:
                with sr.Microphone() as source:
                    recognizer.adjust_for_ambient_noise(source, duration=0.2)
                    while ecoute_active.is_set() and not ia_parle.is_set():
                        try:
                            audio = recognizer.listen(source, timeout=1.5, phrase_time_limit=8.0)
                            if ecoute_active.is_set() and not ia_parle.is_set():
                                texte = recognizer.recognize_google(audio, language="fr-FR").strip()
                                if texte:
                                    saisie_queue.put(("vocal", texte))
                                    break
                        except (sr.WaitTimeoutError, sr.UnknownValueError):
                            pass
                        except Exception:
                            break
            except Exception:
                time.sleep(0.3)
        else:
            time.sleep(0.1)


# ==============================
# ÉCOUTE CLAVIER EN CONTINU
# ==============================
def thread_ecoute_clavier():
    """Capture la saisie au clavier."""
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break
            texte = line.strip()
            if texte:
                saisie_queue.put(("clavier", texte))
        except Exception:
            break


# ==============================
# NETTOYAGE DU TEXTE POUR TTS
# ==============================
def nettoyer_texte_pour_vocal(texte):
    """Retire la mise en forme Markdown et les symboles spéciaux pour une lecture vocale naturelle."""
    if not texte:
        return ""
    texte = re.sub(r'[*#_~`]+', '', texte)
    texte = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', texte)
    texte = re.sub(r'^\s*[\-\*\•]\s*', '', texte, flags=re.MULTILINE)
    texte = re.sub(r'\n+', '. ', texte)
    return texte.strip()


# ==============================
# PARLER AVEC COUPURE
# ==============================
async def _generer_audio(texte, chemin):
    """Génère le fichier audio avec edge-tts."""
    communicate = edge_tts.Communicate(texte, voice="fr-FR-DeniseNeural")
    await communicate.save(chemin)


def parler(texte):
    texte_vocal = nettoyer_texte_pour_vocal(texte)
    if not texte_vocal:
        return

    chemin = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
            chemin = f.name

        asyncio.run(_generer_audio(texte_vocal, chemin))

        interrompu.clear()
        ia_parle.set()

        pygame.mixer.music.load(chemin)
        pygame.mixer.music.play()

        while pygame.mixer.music.get_busy():
            if interrompu.is_set():
                pygame.mixer.music.stop()
                break
            pygame.time.Clock().tick(10)

    except Exception as e:
        print(f"[Erreur voix] {e}")
    finally:
        ia_parle.clear()
        try:
            pygame.mixer.music.unload()
        except Exception:
            pass
        if chemin and os.path.exists(chemin):
            try:
                os.remove(chemin)
            except Exception:
                pass


# ==============================
# RÉINITIALISATION DE LA SESSION
# ==============================
def est_demande_changement(question):
    """Vérifie si l'utilisateur souhaite réinitialiser la conversation."""
    q = question.lower().strip()
    mots_cles = ["reset", "recommencer", "reinitialiser", "réinitialiser", "nouveau"]
    return any(mc == q or q.startswith(mc) for mc in mots_cles)


# ==============================
# ENVOYER À L'IA
# ==============================
def executer_requete_ia(messages):
    """Envoie la liste des messages à l'API et retourne le contenu de la réponse."""
    try:
        response = client.chat.completions.create(model=MODEL, messages=messages)
        return response.choices[0].message.content
    except Exception as e:
        return f"Erreur API : {e}"


def envoyer(question):
    global historique

    if est_demande_changement(question):
        historique = [{"role": "system", "content": SYSTEM_PROMPT}]
        prompt_reset = "Salue à nouveau ton créateur PHANUEL en l'appellant MY LORD et demande-lui comment tu peux l'aider aujourd'hui."
        reponse = executer_requete_ia([{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": prompt_reset}])
        if not reponse.startswith("Erreur API"):
            historique.append({"role": "assistant", "content": reponse})
        return reponse

    historique.append({"role": "user", "content": question})
    reponse = executer_requete_ia(historique)

    if reponse.startswith("Erreur API"):
        historique.pop()
    else:
        historique.append({"role": "assistant", "content": reponse})

    return reponse


# ==============================
# DÉMARRAGE HYBRIDE (VOCAL + CLAVIER)
# ==============================
pygame.mixer.init()
historique = [{"role": "system", "content": SYSTEM_PROMPT}]

print("\n" + "=" * 55)
print("        PH.AI — Toujours disponible for my LORD !")
print("=" * 55)
print("✅ MODE HYBRIDE ACTIVÉ (Vocal + Écrit simultanés)")
print("👉 Vous pouvez PARLER au micro OU TAPER au clavier à tout moment !")
print("👉 Dites 'ATTEND' ou 'STOP' pour couper la parole à PH.AI.")
print("👉 Tapez ou dites 'quitter' pour fermer, 'reset' pour recommencer.\n")
print("=" * 55 + "\n")

# Lancement des threads d'écoute
t_surveillance = threading.Thread(target=surveiller_micro, daemon=True)
t_surveillance.start()

t_vocal = threading.Thread(target=thread_ecoute_vocale, daemon=True)
t_vocal.start()

t_clavier = threading.Thread(target=thread_ecoute_clavier, daemon=True)
t_clavier.start()

# Premier message d'accueil de PH.AI pour PHANUEL
reponse_ia = envoyer("Bonjour PH.AI ! Présente-toi brièvement à ton créateur PHANUEL en l'appellant MY LORD (prononce ça en anglais) et demande-lui comment tu peux l'aider today.")
print(f"PH.AI : {reponse_ia}\n")
parler(reponse_ia)

# Activer l'écoute pour les questions de l'utilisateur
ecoute_active.set()

# ==============================
# BOUCLE PRINCIPALE HYBRIDE
# ==============================
while True:
    try:
        # Attendre une entrée provenant du micro OU du clavier
        source_type, question = saisie_queue.get()

        if not question:
            continue

        # Désactiver l'écoute vocale des questions pendant que PH.AI traite et parle
        ecoute_active.clear()

        # Afficher la provenance de la question
        if source_type == "vocal":
            print(f"\n🎤 Toi (Vocal) : {question}")
        else:
            print(f"\n⌨️ Toi (Clavier) : {question}")

        if question.lower() in ("quitter", "quit", "exit", "q"):
            msg = "Goodbye my LORD ! Always at your service. Have a great day !"
            print(f"\nPH.AI : {msg}")
            parler(msg)
            break

        reponse_ia = envoyer(question)
        print(f"\nPH.AI : {reponse_ia}\n")
        parler(reponse_ia)

        # Réactiver l'écoute vocale pour la question suivante
        ecoute_active.set()

    except KeyboardInterrupt:
        break