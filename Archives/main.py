# Fichier : main.py
import tkinter as tk
from Archives.interface import GalvoInterface

def main():
    # Crée la fenêtre principale
    root = tk.Tk()
    
    # Charge notre interface dedans
    app = GalvoInterface(root)
    
    # Lance la boucle de l'application (pour qu'elle reste ouverte)
    root.mainloop()

if __name__ == "__main__":
    main()