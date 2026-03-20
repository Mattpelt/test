"""
Script d'authentification OAuth2 Gmail — à lancer UNE SEULE FOIS sur le serveur.

Prérequis :
  1. Créer un projet sur https://console.cloud.google.com
  2. Activer l'API Gmail
  3. Créer des identifiants OAuth2 "Application de bureau"
  4. Télécharger le fichier JSON et le renommer credentials.json
  5. Le placer dans le dossier gmail_credentials/ à la racine du projet
  6. Lancer ce script : python scripts/gmail_auth.py

Le script génère gmail_credentials/token.json qui sera utilisé par le poller.
Ce token contient un refresh_token permanent — il n'est plus nécessaire de
relancer ce script sauf si les permissions sont révoquées.

Sur un serveur sans interface graphique, utiliser le flag --console :
  python scripts/gmail_auth.py --console
"""

import argparse
import sys
from pathlib import Path

CREDENTIALS_DIR = Path(__file__).parent.parent / "gmail_credentials"
CREDENTIALS_FILE = CREDENTIALS_DIR / "credentials.json"
TOKEN_FILE = CREDENTIALS_DIR / "token.json"
SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]


def main():
    parser = argparse.ArgumentParser(description="Auth OAuth2 Gmail pour SkyDive Media Hub")
    parser.add_argument(
        "--console",
        action="store_true",
        help="Mode console (serveur sans navigateur) : affiche l'URL à visiter manuellement",
    )
    args = parser.parse_args()

    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        print("Dépendance manquante. Installer avec :")
        print("  pip install google-auth-oauthlib google-auth-httplib2 google-api-python-client")
        sys.exit(1)

    if not CREDENTIALS_FILE.exists():
        print(f"Fichier credentials.json introuvable : {CREDENTIALS_FILE}")
        print("Télécharger depuis Google Cloud Console → APIs & Services → Identifiants")
        sys.exit(1)

    CREDENTIALS_DIR.mkdir(parents=True, exist_ok=True)
    flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)

    if args.console:
        # Mode serveur headless : redirect vers localhost (page d'erreur normale)
        flow.redirect_uri = "http://localhost"
        auth_url, _ = flow.authorization_url(prompt="consent")
        print("\nOuvre cette URL dans ton navigateur :")
        print(f"\n  {auth_url}\n")
        print("Après connexion, le navigateur affichera une erreur 'localhost refused'.")
        print("C'est normal — copie l'URL COMPLÈTE de la barre d'adresse et colle-la ici.")
        redirect_response = input("\nURL complète de redirection : ").strip()
        flow.fetch_token(authorization_response=redirect_response)
        creds = flow.credentials
    else:
        # Mode local : ouvre le navigateur automatiquement
        creds = flow.run_local_server(port=0)

    TOKEN_FILE.write_text(creds.to_json())
    print(f"\nAuthentification réussie. Token enregistré dans : {TOKEN_FILE}")
    print("Le poller Gmail démarrera automatiquement au prochain restart du backend.")


if __name__ == "__main__":
    main()
