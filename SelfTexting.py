import logging

import requests

import config


def send_push(title, message):
    """Notification Pushbullet, best-effort : ne lève jamais."""
    if not config.pb_token:
        return

    headers = {
        'Access-Token': config.pb_token,
        'Content-Type': 'application/json',
    }

    json_data = {
        'body': message,
        'title': title,
        'type': 'note',
        'device_iden' : config.pushbutton_device_iden
    }

    try:
        requests.post('https://api.pushbullet.com/v2/pushes', headers=headers, json=json_data, timeout=10)
    except requests.RequestException as err:
        logging.debug(f"Pushbullet injoignable : {err}")


if __name__ == "__main__":
    send_push("test", "test config")
