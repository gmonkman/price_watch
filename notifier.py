import requests
from abc import ABC as _ABC

import fuckit as _fuckit

import funclite.stringslib as _stringslib

from orm import Log as _Log
from enums import *

__all__ = ['PushBullet', 'Telegram', 'WhatsApp', 'TwilioSMS']
try:
    import pywhatkit as _pywhatkit  # noqa
except ImportError:
    print('Failed to import pywhatkit.')
    _pywhatkit = None

try:
    from pushbullet import Pushbullet as _Pushbullet
except ImportError:
    print('Failed to import pushbullet.')
    _Pushbullet = None

try:
    from pushbullet import Pushbullet as _Pushbullet
except ImportError:
    print('Failed to import pushbullet.')
    _Pushbullet = None

try:
    from twilio.rest import Client as _TwilioClient
except ImportError:
    print('Failed to import twilio.')
    _TwilioClient = None

import config as _config


class Telegram(_ABC):
    """
    This is a namespace class for Telegram notifications
    to the user defined in config.py

    Methods:
        send: Send notification message
    """

    @staticmethod
    def send(title: str, body: str, monitorid: int = None) -> None:
        """
            Sends message to chat.
            Telegram has no seperate title however, it is in this method for consistency.
            The title and body are concatenated with a newline

            Parameters:
            title(str): Title of the message
             body(str): The string of the message to be sent
             monitorid(int): The monitorid of the chat, this is optional and is used for logging purposes
        """
        message = f'{title}\n\n{body}'
        try:
            data = {
                "chat_id": _config.Telegram.chat_id,
                "text": message
            }
            headers = {'Content-Type': 'application/json'}
            url = f"https://api.telegram.org/bot{_config.Telegram.bot_token}/sendMessage"
            requests.post(url, json=data, headers=headers)
        except Exception as e:
            _logit('Telegram', monitorid, e)


class WhatsApp(_ABC):
    """
    This is a namespace class for WhatsApp notifications
    to the phone number in config.py

    Methods:
        send: Send notification message with WhatsApp
    """

    @staticmethod
    def send(message: str, monitorid: int = None) -> None:
        try:
            _pywhatkit.sendwhatmsg_instantly(_config.WhatsApp.phone_nr, message, 0, True)
        except Exception as e:
            _logit('WhatsApp', monitorid, e)


class PushBullet(_ABC):
    """
    This is a namespace class for Pushbullet notifications

    Methods:
        send: Send notification message with Pushbullet
    """

    @staticmethod
    def send(title: str, body: str, monitorid: int = None) -> None:
        try:
            Pb = _Pushbullet(_config.Pushbullet.token)
            Pb.push_note(title, body)
        except Exception as e:
            _logit('PushBullet', monitorid, e)


class TwilioSMS(_ABC):
    """
    This is a namespace class for SMS notifications provided by the twilio SaaS

    Methods:
        send: Send notification message with Pushbullet
    """

    @staticmethod
    def send(title: str, body: str, monitorid: int = None) -> None:
        """
        Send SMS message with TwilioSMS.
        SMS messages don't support titles however, it is in this method for consistency.
        The title and body are concatenated with a newline.

        Args:
            title: Title of the message
            body: Body of the message
            monitorid: Monitorid, used for logging purposes

        Returns:
            None
        """
        message = f'{title}\n\n{body}'
        try:
            TC = _TwilioClient(_config.TwilioSMS.account_sid, _config.TwilioSMS.auth_token)
            M = TC.messages.create(body=message, to=_config.TwilioSMS.send_to_phone, from_=_config.TwilioSMS.send_from_phone)
            print(M.body)
        except Exception as e:
            _logit('TwilioSMS', monitorid, e)


# region helper methods
def _logit(notifier: str, monitorid: int | None, e: Exception) -> None:
    with _fuckit:
        Log_ = _Log()  # noqa
        Log_.monitorid = monitorid  # noqa
        Log_.action = f'{self.parser} {EnumLogAction.Notify.value}'  # noqa
        Log_.level = EnumLogLevel.ERROR.value  # noqa
        Log_.when = _stringslib.pretty_date_now(with_time=True)
        Log_.comment = f'Failed to send {notifier} notification for monitorid {monitorid}.\n\nThe error was:\n{repr(e)}'  # noqa
        Log_.save()
        print(Log_.comment)
# endregion helper methods






if __name__ == "__main__":
    pass
