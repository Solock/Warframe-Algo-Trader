"""
Récupère un token warframe.market et l'enregistre dans config.json.

Usage : python getWFMtoken.py
L'email et le mot de passe sont saisis localement (mot de passe masqué),
envoyés uniquement à api.warframe.market, jamais stockés.
"""
import getpass
import json
import os

from AccessingWFMarket import login

if __name__ == "__main__":
    email = input("Email warframe.market : ").strip()
    password = getpass.getpass("Mot de passe (saisie masquée) : ")
    platform = input("Plateforme [pc] : ").strip().lower() or "pc"

    ingameName, token = login(email, password, platform)
    if token is None:
        raise SystemExit("Échec du login — vérifie email/mot de passe.")

    if not os.path.exists("config.json"):
        raise SystemExit("config.json introuvable — lance d'abord : python init.py")

    with open("config.json") as f:
        configData = json.load(f)
    configData["wfm_jwt_token"] = token.split(" ")[-1]
    configData["inGameName"] = ingameName
    configData["platform"] = platform
    with open("config.json", "w") as f:
        f.write(json.dumps(configData, indent=4))

    print(f"OK — connecté en tant que {ingameName}, token enregistré dans config.json")
