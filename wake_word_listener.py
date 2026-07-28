import speech_recognition as sr
import subprocess
import sys
import os
import time

# Configurer l'encodage de la console sous Windows pour éviter UnicodeEncodeError
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Mots d'activation reconnus (Mots-clés principaux : LET'S GO / ARISE)
WAKE_WORDS = [
    "let's go",
    "lets go",
    "lesgo",
    "letgo",
    "let us go",
    "arise", 
    "hey arise", 
    "ok arise", 
    "dis arise", 
    "lancer arise",
    "ouvre arise",
    "rise"
]

def ecouter_wake_word():
    recognizer = sr.Recognizer()
    # Sensibilité maximale du micro
    recognizer.energy_threshold = 150  # Seuil bas = Micro hyper sensible
    recognizer.dynamic_energy_threshold = False  # Empêche le micro de devenir trop dur à réveiller

    print("\n" + "=" * 55)
    print(" SERVEUR VOCAL PH.AI — Mot-clé : LET'S GO / ARISE")
    print("=" * 55)
    print("Dites simplement 'LET'S GO' ou 'ARISE'")
    print("pour démarrer PH.AI (Toujours disponible for my LORD) !\n")

    while True:
        try:
            with sr.Microphone() as source:
                # Étalonnage très rapide pour ne pas bloquer l'écoute
                recognizer.adjust_for_ambient_noise(source, duration=0.2)
                while True:
                    try:
                        # Écoute très réactive
                        audio = recognizer.listen(source, timeout=2.0, phrase_time_limit=3.5)
                        
                        texte_en = ""
                        texte_fr = ""
                        try:
                            texte_en = recognizer.recognize_google(audio, language="en-US").lower()
                        except Exception:
                            pass

                        try:
                            texte_fr = recognizer.recognize_google(audio, language="fr-FR").lower()
                        except Exception:
                            pass

                        texte_combine = f"{texte_en} {texte_fr}".strip()
                        if texte_combine:
                            print(f"[Son détecté : '{texte_en or texte_fr}']")

                        if any(w in texte_combine for w in WAKE_WORDS):
                            print("\n*** MOT D'ACTIVATION 'LET'S GO' DÉTECTÉ ! Lancement de PH.AI... ***\n")
                            
                            main_path = os.path.join(os.path.dirname(__file__), "main.py")
                            
                            # Lancer main.py via venv/python si disponible
                            python_exe = sys.executable
                            venv_python = os.path.join(os.path.dirname(__file__), "venv", "Scripts", "python.exe")
                            if os.path.exists(venv_python):
                                python_exe = venv_python

                            subprocess.Popen(
                                [python_exe, main_path],
                                creationflags=subprocess.CREATE_NEW_CONSOLE,
                                cwd=os.path.dirname(__file__)
                            )

                            time.sleep(10)
                            print("Reprise de l'écoute du mot d'activation...")

                    except sr.WaitTimeoutError:
                        pass
                    except sr.UnknownValueError:
                        pass
                    except Exception as e:
                        time.sleep(0.3)

        except Exception as e:
            print(f"[Erreur micro arrière-plan] {e}")
            time.sleep(2)

if __name__ == "__main__":
    ecouter_wake_word()
