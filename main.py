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
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
dotenv_path = os.path.join(BASE_DIR, ".env")
load_dotenv(dotenv_path=dotenv_path, override=True)

API_KEY = (os.environ.get("API_KEY") or "").strip()
BASE_URL = "https://api.groq.com/openai/v1"
MODELS = ["groq/compound", "groq/compound-mini", "qwen/qwen3.6-27b", "openai/gpt-oss-120b", "openai/gpt-oss-20b", "llama-3.3-70b-versatile", "llama-3.1-8b-instant"]
SEUIL_VOIX_MAX = 150  # Seuil maximal garanti pour une haute sensibilité (pas besoin de parler fort)

if not API_KEY:
    print("⚠️ ATTENTION : Aucune clé API_KEY valide trouvée dans le fichier .env !")

client = OpenAI(api_key=API_KEY or "DUMMY_KEY", base_url=BASE_URL)

SYSTEM_PROMPT = """Tu es PH.AI, mon IA à moi ton créateur PHANUEL.

TA MÉTHODE DE RÉPONSE (toujours dans cet ordre) :
- Explication claire et simple
- Exemple concret 
- Le savais-tu ? — un fait de culture générale
- Conseil — une astuce pour progresser

TES RÈGLES :
- Mets dans tes réponses quelques trois mots anglais (combinés avec le français) pour rendre la conversation plus naturelle (franc-anglais)
- Tu réponds TOUJOURS en franc-anglais
- Tes réponses vocales sont courtes et claires
- Tu encourages toujours à la fin"""


# ==============================
# ÉÉTAT GLOBAL
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
    recognizer.energy_threshold = 150
    recognizer.dynamic_energy_threshold = True
    recognizer.pause_threshold = 0.6
    MOTS_CLES_INTERRUPTION = ["attend", "attends", "attendez", "stop", "pause", "arret", "arrête", "arrete"]

    while True:
        if ia_parle.is_set():
            time.sleep(0.2)
            if not ia_parle.is_set():
                continue

            try:
                with sr.Microphone() as source:
                    recognizer.adjust_for_ambient_noise(source, duration=0.2)
                    if recognizer.energy_threshold > SEUIL_VOIX_MAX:
                        recognizer.energy_threshold = SEUIL_VOIX_MAX

                    while ia_parle.is_set() and not interrompu.is_set():
                        try:
                            audio = recognizer.listen(source, timeout=1.0, phrase_time_limit=2.0)
                            if ia_parle.is_set():
                                mots_dits = recognizer.recognize_google(audio, language="fr-FR").lower()
                                if any(kw in mots_dits for kw in MOTS_CLES_INTERRUPTION):
                                    pygame.mixer.music.stop()
                                    interrompu.set()
                                    print("\n🛑 [Mot-clé 'ATTEND' / 'STOP' détecté ! PH.AI s'arrête]")
                                    break
                        except (sr.WaitTimeoutError, sr.UnknownValueError):
                            pass
                        except Exception:
                            break
            except Exception:
                time.sleep(0.3)
            finally:
                time.sleep(0.2)
        else:
            time.sleep(0.1)


# ==============================
# ÉÉCOUTE VOCALE DES QUESTIONS (arrière-plan)
# ==============================
def thread_ecoute_vocale():
    """Écoute le microphone quand PH.AI attend une question."""
    recognizer = sr.Recognizer()
    # Micro ultra sensible (seuil bas) + pause de 2.0s pour écouter les phrases longues sans couper !
    recognizer.energy_threshold = 100
    recognizer.dynamic_energy_threshold = True
    recognizer.dynamic_energy_adjustment_damping = 0.15
    recognizer.dynamic_energy_ratio = 1.2
    recognizer.pause_threshold = 2.0  # Attend 2.0 secondes de silence avant de valider la fin de phrase

    mic_annonce = False

    while True:
        if ecoute_active.is_set() and not ia_parle.is_set():
            try:
                with sr.Microphone() as source:
                    recognizer.adjust_for_ambient_noise(source, duration=0.3)
                    # Forcer un seuil d'énergie très sensible pour ne pas obliger l'utilisateur à parler fort
                    if recognizer.energy_threshold > SEUIL_VOIX_MAX:
                        recognizer.energy_threshold = SEUIL_VOIX_MAX

                    if not mic_annonce and ecoute_active.is_set() and not ia_parle.is_set():
                        print("🎤 [Microphone prêt — Parlez !]")
                        mic_annonce = True

                    while ecoute_active.is_set() and not ia_parle.is_set():
                        try:
                            # phrase_time_limit augmenté à 20s pour les questions longues
                            audio = recognizer.listen(source, timeout=4.0, phrase_time_limit=20.0)
                            if ecoute_active.is_set() and not ia_parle.is_set():
                                print("⚡ [Son capté — Analyse en cours...]")
                                texte = recognizer.recognize_google(audio, language="fr-FR").strip()
                                if texte:
                                    mic_annonce = False
                                    saisie_queue.put(("vocal", texte))
                                    break
                        except sr.WaitTimeoutError:
                            pass
                        except sr.UnknownValueError:
                            print("❓ [Voix non comprise — Vous pouvez répéter ou continuer votre phrase]")
                        except Exception as e:
                            print(f"[⚠️ Erreur écoute vocale] {e}")
                            break
            except Exception as e:
                time.sleep(0.5)
        else:
            mic_annonce = False
            time.sleep(0.1)


# ==============================
# ÉÉCOUTE CLAVIER EN CONTINU
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
    """Envoie la liste des messages à l'API avec gestion automatique de fallback en cas d'erreur de modèle."""
    derniere_erreur = None
    for model_name in MODELS:
        try:
            response = client.chat.completions.create(model=model_name, messages=messages)
            return response.choices[0].message.content
        except Exception as e:
            derniere_erreur = e
            continue
    return f"Erreur API : {derniere_erreur}"


def envoyer(question):
    global historique

    if est_demande_changement(question):
        prompt_reset = "Salue à nouveau ton créateur PHANUEL en l'appellant MY LORD (prononce ça en anglais) et demande-lui comment tu peux l'aider aujourd'hui."
        historique = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt_reset}
        ]
        reponse = executer_requete_ia(historique)
        if reponse.startswith("Erreur API"):
            historique.pop()
        else:
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
if reponse_ia.startswith("Erreur API"):
    parler("Désolé my LORD, j'ai rencontré un problème de connexion avec le serveur.")
else:
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
        if reponse_ia.startswith("Erreur API"):
            parler("Désolé my LORD, j'ai rencontré un problème de connexion avec le serveur.")
        else:
            parler(reponse_ia)

        # Réactiver l'écoute vocale pour la question suivante
        ecoute_active.set()

    except KeyboardInterrupt:
        break