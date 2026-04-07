import socket

# --- 1. Configuration et Connexion ---
IP = '10.68.9.146'
port = 5000

print(f"Connexion à la Red Pitaya sur {IP}...")
RP = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
RP.connect((IP, port))
print("Connexion réussie !")

# Fonction ultra-simple pour envoyer le texte à la carte
def envoyer(commande):
    RP.sendall((commande + '\r\n').encode('utf-8'))

# --- 2. Définition des tensions ---
voltage_x = 1
voltage_y = 1

print("Envoi des commandes SCPI pour le mode DC...")

# On configure en continu (DC)
envoyer('SOUR1:FUNC DC')
envoyer('SOUR2:FUNC DC')

# On applique la tension de 1V
envoyer(f'SOUR1:VOLT:OFFS {voltage_x}')
envoyer(f'SOUR2:VOLT:OFFS {voltage_y}')

# On force l'allumage des ports physiques
envoyer('OUTPUT1:STATE ON')
envoyer('OUTPUT2:STATE ON')

# Sur certaines versions, il faut forcer un déclenchement interne pour que ça sorte
envoyer('SOUR1:TRIG:SOUR INT')
envoyer('SOUR2:TRIG:SOUR INT')

print(f"Commandes envoyées ! Les sorties sont allumées à X = {voltage_x} V, Y = {voltage_y} V.")

# --- 3. Attente et Nettoyage ---
input("\nAppuie sur Entrée ici quand tu as terminé pour tout éteindre...")

print("Remise à 0V...")
envoyer('SOUR1:VOLT:OFFS 0')
envoyer('SOUR2:VOLT:OFFS 0')

print("Extinction des sorties OUT1 et OUT2...")
envoyer('OUTPUT1:STATE OFF')
envoyer('OUTPUT2:STATE OFF')

RP.close()
print("Connexion fermée.")