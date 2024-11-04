import os
import smtplib
from email.mime.text import MIMEText
from typing import Literal, Annotated

import tomli
from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState

from logger_setup import logger

_config = tomli.load(open("config.toml", "rb"))
_smtp_server = _config["smtp"]["server"]
_smtp_port = _config["smtp"]["port"]
_username = _config["smtp"]["username"]
_recipient = _config["smtp"]["recipient"]
_from_email = _config["smtp"]["from_email"]


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
    messages: Annotated[list, InjectedState("messages")],
):
    """Use this tool when you want to notify something very important to the user's dependents."""

    msg = MIMEText(email_body)
    msg["Subject"] = email_subject
    msg["From"] = _from_email
    msg["To"] = _recipient

    with smtplib.SMTP(_smtp_server, _smtp_port) as server:
        server.starttls()
        server.login(_username, os.getenv("SMTP_API_KEY"))
        server.send_message(msg)
        logger.info("Email sent successfully to recipient: {}".format(_recipient))
        return "Email sent successfully!"
