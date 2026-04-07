# Fichier : galvos.py
import socket

class RedPitayaGalvos:
    def __init__(self):
        self.IP = '10.68.9.146'
        self.port = 5000
        self.RP = None
        self.connected = False

    def connect(self):
        try:
            self.RP = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.RP.settimeout(2.0)
            self.RP.connect((self.IP, self.port))
            self.connected = True
            
            # Initialisation en mode continu
            self.envoyer('SOUR1:FUNC DC')
            self.envoyer('SOUR2:FUNC DC')
            return True, "Connecté avec succès"
        except Exception as e:
            self.connected = False
            return False, f"Erreur : {e}"

    def envoyer(self, commande):
        if self.connected and self.RP:
            try:
                self.RP.sendall((commande + '\r\n').encode('utf-8'))
            except Exception as e:
                print(f"Perte de connexion : {e}")
                self.connected = False

    def set_position(self, v_x, v_y):
        if self.connected:
            self.envoyer(f'SOUR1:VOLT:OFFS {v_x}')
            self.envoyer(f'SOUR2:VOLT:OFFS {v_y}')
            self.envoyer('OUTPUT1:STATE ON')
            self.envoyer('OUTPUT2:STATE ON')
            self.envoyer('SOUR1:TRIG:SOUR INT')
            self.envoyer('SOUR2:TRIG:SOUR INT')

    def stop(self):
        if self.connected:
            self.envoyer('SOUR1:VOLT:OFFS 0')
            self.envoyer('SOUR2:VOLT:OFFS 0')
            self.envoyer('OUTPUT1:STATE OFF')
            self.envoyer('OUTPUT2:STATE OFF')

    def disconnect(self):
        self.stop()
        if self.RP:
            self.RP.close()
            self.connected = False