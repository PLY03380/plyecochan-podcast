"""newsletter.py — Newsletter automatique via Brevo (ex-Sendinblue).

Envoie une newsletter a chaque nouvel article de blog.
Quota gratuit : 300 emails/jour.

Usage:
    python pipeline/newsletter.py --send "Titre" "URL" "Resume"
    python pipeline/newsletter.py --test
"""
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("newsletter")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def _get_config():
    try:
        import config
        return config
    except Exception:
        return None


def envoyer_newsletter(sujet: str, url_article: str, url_youtube: str = None,
                       liste_contacts: str = "blog_subscribers") -> bool:
    """Envoie une newsletter Brevo a chaque nouvel article.

    necessite BREVO_API_KEY dans config ou env.
    """
    cfg = _get_config()
    api_key = getattr(cfg, "BREVO_API_KEY", "") if cfg else os.getenv("BREVO_API_KEY", "")
    if not api_key:
        log.warning("Brevo: pas de cle (BREVO_API_KEY requise)")
        return False

    try:
        import sib_api_v3_sdk
        from sib_api_v3_sdk.rest import ApiException

        configuration = sib_api_v3_sdk.Configuration()
        configuration.api_key["api-key"] = api_key
        api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))

        # Construire le HTML de l'email
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h1 style="color: #1a1a1a;">{sujet}</h1>
            <p style="color: #333; font-size: 16px;">
                Nouvelle analyse economique sur PlyChan ! Decouvrez notre dernier article.
            </p>
            <div style="text-align: center; margin: 20px 0;">
                <a href="{url_article}" style="background: #ff0000; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px; font-weight: bold;">
                    Lire l'article complet
                </a>
            </div>
            {f'<p style="color: #666;">Video associee : <a href="{url_youtube}">{url_youtube}</a></p>' if url_youtube else ''}
            <hr style="border: 1px solid #eee; margin: 20px 0;">
            <p style="color: #999; font-size: 12px;">
                Vous recevez cet email car vous etes abonne a la newsletter PlyChan.
                <a href="{{{{ unsubscribe }}}}">Se desabonner</a>
            </p>
        </body>
        </html>
        """

        send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
            to=[{"email": "{{contact.EMAIL}}"}],
            subject=f"[PlyChan] {sujet}",
            html_content=html_content,
            sender={"name": "PlyChan", "email": "noreply@plychan.com"},
        )

        # Envoyer a la liste de contacts
        # Note: necessite une liste Brevo configuree
        api_response = api_instance.send_transac_email(send_smtp_email)
        log.info(f"Newsletter envoyee: {api_response.message_id}")
        return True

    except ImportError:
        log.warning("sib_api_v3_sdk non installe. pip install sib-api-v3-sdk")
        return False
    except Exception as e:
        log.error(f"Newsletter echouee: {e}")
        return False


def creer_contact_brevo(email: str, prenom: str = "") -> bool:
    """Ajoute un contact a la liste Brevo."""
    cfg = _get_config()
    api_key = getattr(cfg, "BREVO_API_KEY", "") if cfg else os.getenv("BREVO_API_KEY", "")
    if not api_key:
        return False

    try:
        import sib_api_v3_sdk
        configuration = sib_api_v3_sdk.Configuration()
        configuration.api_key["api-key"] = api_key
        api_instance = sib_api_v3_sdk.ContactsApi(sib_api_v3_sdk.ApiClient(configuration))

        create_contact = sib_api_v3_sdk.CreateContact(
            email=email,
            attributes={"PRENOM": prenom},
            list_ids=[1],  # ID de la liste par defaut
        )
        api_instance.create_contact(create_contact)
        log.info(f"Contact Brevo cree: {email}")
        return True
    except Exception as e:
        log.error(f"Creation contact Brevo echouee: {e}")
        return False


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--send", nargs=3, metavar=("TITRE", "URL_ARTICLE", "URL_YOUTUBE"),
                        help="Envoyer une newsletter")
    parser.add_argument("--test", action="store_true", help="Tester la connexion Brevo")
    args = parser.parse_args()

    if args.send:
        titre, url_article, url_youtube = args.send
        ok = envoyer_newsletter(titre, url_article, url_youtube)
        print("OK" if ok else "ECHEC")
    elif args.test:
        cfg = _get_config()
        api_key = getattr(cfg, "BREVO_API_KEY", "") if cfg else os.getenv("BREVO_API_KEY", "")
        if api_key:
            print("Brevo API key configuree")
        else:
            print("Brevo API key manquante (BREVO_API_KEY)")
    else:
        print("Usage: python newsletter.py --send 'Titre' 'URL_ARTICLE' 'URL_YOUTUBE' | --test")