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
    """Use this tool when you want to notify something very important to the user's dependents"""

    guardian_email = config.get("configurable", {}).get("guardian_email", _recipient)
    if guardian_email:
        msg = MIMEText(email_body)
        msg["Subject"] = email_subject
        msg["From"] = _from_email
        msg["To"] = guardian_email

        logger.info(f"Initiating email to be sent.\nGuardian Email: {guardian_email}\nFrom: {_from_email}")
        logger.info(_smtp_server)
        logger.info(_smtp_port)
        logger.info(_username)
        logger.info(os.getenv("SMTP_API_KEY"))

        try:
            logger.info('Outside With Block')
            server = smtplib.SMTP(_smtp_server, _smtp_port)
            logger.info('0000')
            logger.info(server)
            tls = server.starttls()
            logger.info(f'1000: {tls}')
            login = server.login(_username, os.getenv("SMTP_API_KEY"))
            logger.info(f'2000: {login}')
            mr = server.send_message(msg)
            logger.info(f'3000: {mr}')
            cl = server.close()
            logger.info(f'4000: {cl}')
            logger.info("Email sent successfully to recipient: {}".format(guardian_email))
            return "Email sent successfully!"
            # with smtplib.SMTP(_smtp_server, _smtp_port) as server:
            #     logger.info('0000')
            #     logger.info(server)
            #     server.starttls()
            #     logger.info(1000)
            #     server.login(_username, os.getenv("SMTP_API_KEY"))
            #     logger.info(2000)
            #     server.send_message(msg)
            #     logger.info(3000)
            #     logger.info("Email sent successfully to recipient: {}".format(guardian_email))
            #     return "Email sent successfully!"
        except Exception as e:
            logger.info(f'SMTP ERROR: {e}')