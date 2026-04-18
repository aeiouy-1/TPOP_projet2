import oceandirect.OceanDirectAPI as od

def test_connexion():
    # 1. Création de l'objet principal (Point d'entrée de l'API)
    # On initialise l'interface pour communiquer avec le matériel
    api = od.OceanDirectAPI()

    # 2. Chercher les appareils connectés (USB/Réseau)
    # Cette fonction renvoie une liste d'identifiants (IDs)
    device_ids = api.get_device_ids()

    if not device_ids:
        print("Aucun spectromètre n'est détecté.")
        return

    # 3. Ouvrir le premier spectromètre trouvé
    # On utilise le premier ID de la liste pour établir la connexion
    device_id = device_ids[0]
    device = api.open_device(device_id)

    print(f"Succès ! Modèle détecté : {device.get_model_name()}")

    # 4. Petite lecture de test (Spectrum Acquisition)
    # On accède au module qui gère la capture du spectre
    acq = device.get_spectrum_acquisition_control()
    
    # On définit le temps d'intégration (en microsecondes)
    # Important pour ton scan : plus c'est long, plus tu captes de lumière
    acq.set_integration_time_micros(100000)

    # Capture et formatage du spectre (lecture des pixels)
    spectre = acq.get_formatted_spectrum()
    print(f"Lecture terminée : {len(spectre)} points de données reçus.")

    # 5. Toujours fermer la connexion pour libérer le port USB
    device.close()


test_connexion()
print("Hello World")