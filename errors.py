"""Custom errors"""
__all__ = ['CaptchaError', 'DBWhatInvalidStringError']


class CaptchaError(Exception):
    pass

class DBWhatInvalidStringError(Exception):
    pass