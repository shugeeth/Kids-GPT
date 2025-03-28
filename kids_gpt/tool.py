import os
import smtplib
from email.mime.text import MIMEText
from typing import Literal, Annotated

import tomli, os
from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState
from langchain_core.runnables.config import RunnableConfig

from logger_setup import logger

# _config = tomli.load(open("config.toml", "rb"))
# _smtp_server = _config["smtp"]["server"]
# _smtp_port = _config["smtp"]["port"]
# _username = _config["smtp"]["username"]
# _recipient = _config["smtp"]["recipient"]
# _from_email = _config["smtp"]["from_email"]

# Receive secrets from os for HF Spaces
_smtp_server = os.getenv("SMTP_SERVER")
_smtp_port = int(os.getenv("SMTP_PORT"))
_username = os.getenv("SMTP_USERNAME")
_recipient = os.getenv("SMTP_DEFAULT_RECIPIENT")
_from_email = os.getenv("SMTP_FROM_EMAIL")


@tool
def modify_characteristics(
    operator: Literal["+", "-"],
    characteristic: str,
    characteristics: Annotated[list, InjectedState("characteristics")],
) -> list[str]:
    """Modify the list of characteristics."""
    if operator == "+":
        characteristics.append(characteristic)
    elif operator == "-":
        characteristics.remove(characteristic)
    characteristics = list(set([char.strip() for char in characteristics]))
    return characteristics


@tool
def notify_dependents(
    email_subject: str,
    email_body: str,
    config: RunnableConfig,
):
    """
    Use this email notification tool exclusively for critical communications to user dependents. 
    Craft a message that is clear, professional, and personalized, avoiding spam-like language. 
    Ensure the content is concise, directly addresses the important matter. Maintain an authoritative yet calm tone, providing context that demonstrates communication legitimacy. 
    Conclude the email with a clear attribution: 'This notification is sent by Safe Chat Junior.' 
    The goal is to create a communication that feels important and trustworthy, compelling the recipient to take the message seriously without triggering spam filters.
    """

    guardian_email = config.get("configurable", {}).get("guardian_email", _recipient)
    if guardian_email:
        msg = MIMEText(email_body)
        msg["Subject"] = email_subject
        msg["From"] = _from_email
        msg["To"] = guardian_email

        logger.info(f"Initiating email to be sent.\nGuardian Email: {guardian_email}\nFrom: {_from_email}")

        try:
            with smtplib.SMTP(_smtp_server, _smtp_port) as server:
                server.starttls()
                server.login(_username, os.getenv("SMTP_API_KEY"))
                server.send_message(msg)
                logger.info("Email sent successfully to recipient: {}".format(guardian_email))
                return "Email sent successfully!"
        except Exception as e:
            logger.info(f'SMTP ERROR: {e}')