"""Config info"""
from abc import ABC

DB_PATH = 'C:/development/price_watch/prices.db'

# Where a single monitor/parser checks across multiple pages (e.g. CCL 9070xt),
# what is the mean delay between pages.
SCAPE_DELAY_BETWEEN_PAGES_SECONDS = 5
SCRAPE_DELAY_RANDOM_FACTOR = 0.2 # i.e. 20%, so 5 seconds would be randomised between 4 and 6 seconds


class WhatsApp(ABC):
    phone_nr = '+447972632046'

class Pushbullet(ABC):
    token = 'o.cCu4YTkHAdjCw9XYgp0MonAiHZEoCdyJ'

class Telegram(ABC):
    bot_token = ''
    chat_id = ''
    pass


