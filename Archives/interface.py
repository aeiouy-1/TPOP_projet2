# Fichier : interface.py
import tkinter as tk
from tkinter import messagebox
from Meas_intensité.galvos import RedPitayaGalvos

class GalvoInterface:
    def __init__(self, root):
        self.root = root
        self.root.title("Contrôle Galvos - Red Pitaya")
        self.root.geometry("400x350")
        self.root.configure(padx=20, pady=20)

        # Instance de notre contrôleur
        self.controleur = RedPitayaGalvos()

        # --- SECTION STATUT ---
        self.lbl_status = tk.Label(root, text="Statut : Déconnecté", fg="red", font=("Arial", 12, "bold"))
        self.lbl_status.pack(pady=10)

        # --- SECTION BOUTONS CONNEXION ---
        frame_conn = tk.Frame(root)
        self.btn_connect = tk.Button(frame_conn, text="Connecter", bg="lightgreen", command=self.connecter)
        self.btn_connect.grid(row=0, column=0, padx=5)
        
        self.btn_disconnect = tk.Button(frame_conn, text="Déconnecter", state=tk.DISABLED, command=self.deconnecter)
        self.btn_disconnect.grid(row=0, column=1, padx=5)
        frame_conn.pack(pady=10)

        # --- SECTION CONTRÔLE (Sliders) ---
        # Slider X
        tk.Label(root, text="Axe X (Volts)").pack()
        self.scale_x = tk.Scale(root, from_=-1.0, to=1.0, resolution=0.01, orient=tk.HORIZONTAL, length=250, command=self.update_position)
        self.scale_x.pack()

        # Slider Y
        tk.Label(root, text="Axe Y (Volts)").pack()
        self.scale_y = tk.Scale(root, from_=-1.0, to=1.0, resolution=0.01, orient=tk.HORIZONTAL, length=250, command=self.update_position)
        self.scale_y.pack()

        # --- SECTION STOP (Mise à zéro) ---
        self.btn_stop = tk.Button(root, text="STOP (Remise à 0V)", bg="salmon", font=("Arial", 10, "bold"), command=self.stop_galvos)
        self.btn_stop.pack(pady=20)

    def connecter(self):
        success, message = self.controleur.connect()
        if success:
            self.lbl_status.config(text="Statut : Connecté", fg="green")
            self.btn_connect.config(state=tk.DISABLED)
            self.btn_disconnect.config(state=tk.NORMAL)
        else:
            messagebox.showerror("Erreur de connexion", message)

    def deconnecter(self):
        self.controleur.disconnect()
        self.lbl_status.config(text="Statut : Déconnecté", fg="red")
        self.btn_connect.config(state=tk.NORMAL)
        self.btn_disconnect.config(state=tk.DISABLED)

    def update_position(self, event=None):
        if self.controleur.connected:
            vx = self.scale_x.get()
            vy = self.scale_y.get()
            self.controleur.set_position(vx, vy)

    def stop_galvos(self):
        # Remet les sliders à 0 et éteint les sorties
        self.scale_x.set(0)
        self.scale_y.set(0)
        if self.controleur.connected:
            self.controleur.stop()