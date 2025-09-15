"""All enums here"""
from enum import Enum as _Enum

__all__ = ['EnumAlertCarriers', 'EnumLogAction', 'EnumLogLevel', 'EnumParsers']


# region Enums
class EnumAlertCarriers(_Enum):
    Email = 'Email'
    PushBullet = 'PushBullet'
    SMS_Twilio = 'SMS_Twilio'
    WhatsApp = 'WhatsApp'

class EnumLogAction(_Enum):
    """Log action enum"""
    Notify = 'Notify'
    Scraping = 'Scraping'
    ScrapingStarted = 'ScrapingStarted'
    ScrapingFinished = 'ScrapingFinished'

class EnumLogLevel(_Enum):
    """Used for the level field in table log"""
    DEBUG = 'DEBUG'
    INFO = 'INFO'
    WARNING = 'WARNING'
    ERROR = 'ERROR'


class EnumParsers(_Enum):
    """Text for the valid parsers we can use"""
    AmazonSingleProduct = 'AmazonSingleProduct'
    Argos = 'Argos'
    AWDIT = 'AWDIT'
    Box = 'Box'
    CashConverters = 'CashConverters'
    CCLOnline = 'CCLOnline'
    Cex = 'Cex'
    Currency = 'Currency'
    ComputerOrbit = 'ComputerOrbit'
    Currys = 'Currys'
    EbaySingleProduct = 'EbaySingleProduct'
    Novatech = 'Novatech'
    Overclockers = 'Overclockers'
    RyobiSingleProduct = 'RyobiSingleProduct'
    Scan = 'Scan'

class EnumNotifiers(_Enum):
    PushBullet = 'PushBullet'
    Telegram = 'Telegram'
    WhatsApp = 'WhatsApp'


# endregion Enums