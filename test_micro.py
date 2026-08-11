import speech_recognition as sr
import sys
import time

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

print("=== DIAGNOSTIC DU MICROPHONE ===")
recognizer = sr.Recognizer()

# Liste des microphones
mics = sr.Microphone.list_microphone_names()
print(f"Nombre de microphones détectés : {len(mics)}")
for idx, name in enumerate(mics):
    print(f"  [{idx}] {name}")

print("\nUtilisation du microphone par défaut...")
try:
    with sr.Microphone() as source:
        print("Microphone ouvert avec succès.")
        print(f"Seuil d'éénergie par défaut : {recognizer.energy_threshold}")
        print("Ajustement au bruit ambiant (0.5s)...")
        recognizer.adjust_for_ambient_noise(source, duration=0.5)
        print(f"Nouveau seuil d'éénergie après ajustement : {recognizer.energy_threshold}")
        
        # Test avec seuil fixe recommandéé (ex: 300)
        recognizer.energy_threshold = 300
        recognizer.dynamic_energy_threshold = True
        recognizer.dynamic_energy_adjustment_damping = 0.15
        recognizer.dynamic_energy_ratio = 1.5

        print("\n--> Écoute active pendant 10 secondes. Parlez maintenant !")
        t_end = time.time() + 10
        while time.time() < t_end:
            try:
                print("En attente de voix (timeout 3s)...")
                audio = recognizer.listen(source, timeout=3.0, phrase_time_limit=5.0)
                print("-> Audio capturéé ! Envoi à Google Speech API...")
                try:
                    texte = recognizer.recognize_google(audio, language="fr-FR")
                    print(f"--> RECONNU (FR) : '{texte}'")
                except sr.UnknownValueError:
                    print("--> Son capté mais non compris par Google (paroles floues ou bruit)")
                except sr.RequestError as e:
                    print(f"--> Erreur de connexion au service Google : {e}")
            except sr.WaitTimeoutError:
                print("--> Aucun son/voix n'a dépassé le seuil d'éénergie pendant les 3 secondes.")

except Exception as e:
    print(f"Erreur d'ouverture du microphone : {e}")
