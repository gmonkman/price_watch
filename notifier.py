import requests
from abc import ABC as _ABC

__all__ = ['PushBullet', 'WhatsApp']
try:
    import pywhatkit as _pywhatkit  # noqa
except ImportError:
    print('Failed to import pywhatkit.')

try:
    from pushbullet import Pushbullet as _Pushbullet
except ImportError:
    print('Failed to import pushbullet.')
    _Pushbullet = None

import config as _config


class Telegram(_ABC):
    """
    This is a namespace class for Telegram notifications
    to the user defined in config.py

    Methods:
        send: Send notification message
    """

    @staticmethod
    def send(message: str) -> None:
        """
            Sends message to chat
            Parameters:
             message(str): The string of the message to be sent
        """
        try:
            data = {
                "chat_id": _config.Telegram.chat_id,
                "text": message
            }
            headers = {'Content-Type': 'application/json'}
            url = f"https://api.telegram.org/bot{_config.Telegram.bot_token}/sendMessage"
            requests.post(url, json=data, headers=headers)
        except Exception as e:
            print(f'Telegram message failed. The error was:\n{repr(e)}')


class WhatsApp(_ABC):
    """
    This is a namespace class for WhatsApp notifications
    to the phone number in config.py

    Methods:
        send: Send notification message with WhatsApp
    """

    @staticmethod
    def send(message: str) -> None:
        _pywhatkit.sendwhatmsg_instantly(_config.WhatsApp.phone_nr, message, 0, True)


class PushBullet(_ABC):
    """
    This is a namespace class for Pushbullet notifications

    Methods:
        send: Send notification message with Pushbullet
    """

    @staticmethod
    def send(title: str, body: str) -> None:
        try:
            Pb = _Pushbullet(_config.Pushbullet.token)
            Pb.push_note(title, body)
        except Exception as e:
            print(f'Pushbullet message failed. The error was:\n{repr(e)}')


if __name__ == "__main__":
    pass
