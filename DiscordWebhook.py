import logging

import requests

import config


def sendMessage(message):
    """Notification Discord via webhook, best-effort : ne lève jamais."""
    if config.webhookLink == "":
        return

    try:
        if config.pingOnNotif:
            r = requests.get(config.webhookLink, timeout=10)
            creatorID = r.json()["user"]["id"]
            msg = {
                "content" : f"<@{creatorID}>, {message}",
            }
        else:
            msg = {
                "content" : f"{message}",
            }

        requests.post(f"{config.webhookLink}", data=msg, timeout=10)
    except (requests.RequestException, KeyError, ValueError) as err:
        logging.debug(f"Webhook Discord injoignable : {err}")


if __name__ == "__main__":
    sendMessage("Testing webhook!")
