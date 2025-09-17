"""Config info"""
from abc import ABC

from enums import EnumNotifiers


DB_PATH = 'C:/development/price_watch/prices.db'

# Where a single monitor/parser checks across multiple pages (e.g. CCL 9070xt),
# what is the mean delay between pages.
SCRAPE_DELAY_BETWEEN_PAGES_SECONDS = 5
SCRAPE_DELAY_RANDOM_FACTOR = 0.2  # i.e. 20%, so 5 seconds would be randomised between 4 and 6 seconds

# Notifiers to use, as enums
NOTIFIERS = [EnumNotifiers.PushBullet]


class WhatsApp(ABC):
    phone_nr = '+44123456789'

class Pushbullet(ABC):
    token = 'o.madeuptoken'

class Telegram(ABC):
    bot_token = ''
    chat_id = ''
    pass


