import sys
import redpitaya_scpi as scpi

IP = '10.68.9.146'
print("Connexion à la Red Pitaya sur " + IP + "...")
rp = scpi.scpi(IP)

# --- TA POSITION FIXE ---
# Modifie ces valeurs (entre -1.0 et 1.0) pour pointer où tu veux
voltage_x = 0.5
voltage_y = 0.2

print("Envoi de la commande de positionnement...")

# Les sorties de la Red Pitaya gardent la dernière tension demandée en mémoire
rp.tx_txt('SOUR1:VOLT ' + str(voltage_x))
rp.tx_txt('SOUR2:VOLT ' + str(voltage_y))

print("Miroirs stabilisés à X=" + str(voltage_x) + "V, Y=" + str(voltage_y) + "V")

# Le programme attend ici indéfiniment. Tu peux faire tes mesures avec le spectromètre.
input("\nPrends ton temps. Appuie sur Entrée quand tu as terminé pour remettre à 0V...")

# --- NETTOYAGE ET SÉCURITÉ ---
print("Remise à 0V des galvos et fermeture de la connexion.")
rp.tx_txt('SOUR1:VOLT 0')
rp.tx_txt('SOUR2:VOLT 0')
rp.close()