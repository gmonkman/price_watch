"""Script that runs the price checker"""
import ast
import random
from datetime import datetime, timedelta
from time import sleep

import dblib.sqlitelib as sqlitelib
import funclite.iolib as iolib
import funclite.stringslib as stringslib

import price_getter
import notifier
import errors
import orm


def main() -> None:
    """
        Every 10 minutes will update prices inside of the database.
    """
    prices = {}
    now = datetime.now()
    error_time = 0


    with sqlitelib.Conn('prices.db') as Conn:
        Crud = sqlitelib.CRUD(Conn)
        cursor = Conn.cursor()
        retrying = False

        first = True
        while True:
            check_interval = 60 * 10 + random.randrange(0, 120)
            interval = 30 + random.randrange(0, 10)

            try:
                right_now = datetime.now()
                if (right_now - now).seconds > 4 * 60 * 60:
                    now = right_now

                print(f"{right_now} ~~ Starting price check...")

                rows = cursor.execute("SELECT productid, parser, url, price, supplier, match_and, match_or FROM monitor").fetchall()
                new_prices = {}
                prices = {}

                PP = iolib.PrintProgress(iter_=rows, init_msg='Reading prices...')
                for row in rows:
                    match_and = ast.literal_eval(row[5])
                    match_or = ast.literal_eval(row[6])
                    if not match_and: match_and = tuple()
                    if not match_or: match_or = tuple()
                    new_prices[row[0]] = price_getter.get_price(row[2], row[1], match_and=match_and, match_or=match_or)  # get_price returns a tuple of price, product url
                    price_alert_threshold = Crud.get_value('product', 'price_alert_threshold', {'productid': row[0]})
                    if new_prices[row[0][0]] < price_alert_threshold and (first or new_prices[row[0][0]] < prices[row[0][0]]):
                        print('Price %s is below threshold %s for product %s' % (new_prices[row[0][0]], price_alert_threshold, row[0]))

                        # Pushbullet
                        notifier.Pushbullet.send(f'{row[0]} in stock at {row[4]} for £{new_prices[row[0][0]]}',
                                                 f'Product {row[0]} in stock at {row[4]} for £{new_prices[row[0][0]]}\n{new_prices[row[0][1]]}')

                if first:
                    prices = new_prices

                print("Updating prices in database...")
                lst = []
                for item in new_prices.items():
                    # sqlite no date type, text date format is "YYYY-MM-DD HH:MM:SS.SSS"
                    # Only update if changes
                    if first or new_prices[row[0][0]] != prices[row[0][0]]:
                        lst += [[item[1][0], stringslib.pretty_date_now(with_time=True), item[1][1], item[0]]]
                        prices[row[0][0]] = new_prices[row[0][0]]

                cursor.executemany("UPDATE monitor SET price = ?, last_run=?, purchase_url=?; WHERE productid = ?", lst)
                Conn.commit()

                if retrying:
                    retrying = False
                    print("Price tracker is connected again!")
                    error_time = 0

                missing = ((right_now + timedelta(seconds=check_interval)) - datetime.now()).seconds
                print(f"Prices updated! {missing} seconds until next check!")
                first = False
                sleep(missing)  # noqa

            except Exception as err:
                print(err)
                error_time += interval
                retrying = True
                print(f"Price tracker has disconnected, retrying in {error_time} seconds!")
                sleep(error_time)  # noqa




if __name__ == '__main__':
    main()
