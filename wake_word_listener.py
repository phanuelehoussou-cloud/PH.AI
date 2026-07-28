import speech_recognition as sr
import subprocess
import sys
import os
import time

# Configurer l'encodage de la console sous Windows pour éviter UnicodeEncodeError
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Mots d'activation reconnus (Mots-clés principaux : LET'S GO / ARISE + variations phonétiques)
WAKE_WORDS = [
    "let's go",
    "lets go",
    "lesgo",
    "letgo",
    "let us go",
    "les go",
    "laisse go",
    "lait se go",
    "lex go",
    "arise", 
    "hey arise", 
    "ok arise", 
    "dis arise", 
    "lancer arise",
    "ouvre arise",
    "rise",
    "aris",
    "erise",
    "a rise"
]

def ecouter_wake_word():
    recognizer = sr.Recognizer()
    recognizer.energy_threshold = 100  # Seuil très réactif pour ne pas obliger à crier
    recognizer.dynamic_energy_threshold = True
    recognizer.dynamic_energy_adjustment_damping = 0.15
    recognizer.dynamic_energy_ratio = 1.2
    recognizer.pause_threshold = 1.5

    print("\n" + "=" * 55)
    print(" SERVEUR VOCAL PH.AI — Mot-clé : LET'S GO / ARISE")
    print("=" * 55)
    print("Dites simplement 'LET'S GO' ou 'ARISE'")
    print("pour démarrer PH.AI (Toujours disponible for my LORD) !\n")

    while True:
        try:
            with sr.Microphone() as source:
                print("[🎤 Micro prêt — En attente du mot d'activation 'LET'S GO' ou 'ARISE'...]")
                recognizer.adjust_for_ambient_noise(source, duration=0.5)
                if recognizer.energy_threshold > 150:
                    recognizer.energy_threshold = 150
                
                while True:
                    try:
                        audio = recognizer.listen(source, timeout=4.0, phrase_time_limit=5.0)
                        print("[⚡ Son détecté ! Analyse en cours...]")
                        
                        texte_reconnu = ""
                        try:
                            texte_reconnu = recognizer.recognize_google(audio, language="fr-FR").lower()
                        except sr.UnknownValueError:
                            try:
                                texte_reconnu = recognizer.recognize_google(audio, language="en-US").lower()
                            except Exception:
                                pass
                        except Exception as e:
                            print(f"[⚠️ Erreur service Google : {e}]")

                        if texte_reconnu:
                            print(f"[🗣️ Entendu : '{texte_reconnu}']")

                            if any(w in texte_reconnu for w in WAKE_WORDS):
                                print("\n" + "★" * 55)
                                print("*** MOT D'ACTIVATION DÉTECTÉ ! Lancement de PH.AI... ***")
                                print("★" * 55 + "\n")
                                
                                main_path = os.path.join(os.path.dirname(__file__), "main.py")
                                python_exe = sys.executable
                                venv_python = os.path.join(os.path.dirname(__file__), "venv", "Scripts", "python.exe")
                                if os.path.exists(venv_python):
                                    python_exe = venv_python

                                process = subprocess.Popen(
                                    [python_exe, main_path],
                                    creationflags=subprocess.CREATE_NEW_CONSOLE,
                                    cwd=os.path.dirname(__file__)
                                )

                                print("📌 PH.AI est en cours d'exécution dans une nouvelle fenêtre.")
                                print("⏳ En attente de la fermeture de PH.AI pour réactiver le mot d'activation...\n")
                                
                                process.wait()
                                
                                print("\n🔄 PH.AI fermé. Reprise de l'écoute du mot d'activation...")
                                break

                    except sr.WaitTimeoutError:
                        pass
                    except sr.UnknownValueError:
                        pass
                    except Exception as e:
                        print(f"[Erreur boucle écoute] {e}")
                        time.sleep(0.3)

        except Exception as e:
            print(f"[Erreur micro] Impossible d'accéder au microphone : {e}")
            time.sleep(2)

if __name__ == "__main__":
    ecouter_wake_word()
