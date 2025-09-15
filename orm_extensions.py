"""
Extensions to the peewee model.
Enables us to regenerate the model using pwiz then set the classes to
inherit from these extensions
"""
import ast as _ast
import requests
import random as _random
from time import sleep as _sleep
from urllib.parse import urlparse as _urlparse

from bs4 import BeautifulSoup
from seleniumbase import SB as _SB
import fuckit as _fuckit
from peewee import *  # noqa

import funclite.stringslib as _stringslib

import errors as _errors
from enums import *
from orm import *
from notifier import PushBullet as _PushBullet
from notifier import WhatsApp as _WhatsApp

__all__ = ['AWDIT', 'AlertExt',
           'LogExt', 'MonitorHistoryExt', 'ProductExt']


class MonitorBaseMixin:
    """Implements reusable code for specific monitor instances"""

    # region instance methods
    def __init__(self, *args, **kwargs):
        self._soups = []
        super().__init__(*args, **kwargs)  # passed to orm.Monitor constructor

    def scrape(self, price: float, product_url: str, product_title: str) -> None:
        """
        Scrape the cheapest price and the product link which has that price.

        The base class handles updating the database tables monitor, monitor_history and logging.

        Args:
            price (float): Price of the product.
            product_url (str): URL of the product.
            product_title (str): Title of the product.
        """
        # Common code to insert monitor history rows. Each scrape event in the inheriting classes
        # can have multiple products below the price threshold
        # No need to capture and log error here, this is wrapped in a try-catch in child scrape method
        P = Product.get(Product.productid == self.productid)  # noqa
        if price and price <= P.price_alert_threshold:
            add_ = True
            MHCheck = MonitorHistory.select().where(
                MonitorHistory.monitorid == self.monitorid,  # noqa
                MonitorHistory.product_title == product_title).order_by(MonitorHistory.date_when.desc()).limit(1)

            if MHCheck:
                for Row in MHCheck:
                    if Row.price != price:
                        DATABASE.execute_sql('update monitor_history set alert_sent=1 where monitorid=? and product_url=?',
                                             (self.monitorid, product_url))  # noqa
                    else:
                        add_ = False

            if add_:
                MH = MonitorHistory()
                MH.monitorid = self.monitorid  # noqa
                MH.price = price
                MH.product_url = product_url
                MH.product_title = _clean_str(product_title)
                MH.date_when = _stringslib.pretty_date_now(with_time=True)
                MH.save()

    def _log_scrape_started(self) -> None:
        # Dont move this to the init. The peewee model wont be initialised.
        Log_ = Log()  # noqa
        Log_.monitorid = self.monitorid  # noqa
        Log_.action = f'{self.parser} {EnumLogAction.ScrapingStarted.value}'  # noqa
        Log_.level = EnumLogLevel.INFO.value  # noqa
        Log_.when = _stringslib.pretty_date_now(with_time=True)
        Log_.comment = f'Started scraping {self.parser} at {self.url}.\nMonitorid:{self.monitorid}'  # noqa
        Log_.save()

    def _log_scrape_complete(self) -> None:
        Log_ = Log()  # noqa
        Log_.monitorid = self.monitorid  # noqa
        Log_.action = f'{self.parser} {EnumLogAction.ScrapingStarted.value}'  # noqa
        Log_.level = EnumLogLevel.INFO.value  # noqa
        Log_.when = _stringslib.pretty_date_now(with_time=True)
        Log_.comment = f'Finished scraping {self.parser} at {self.url}.\nMonitorid:{self.monitorid}'  # noqa
        Log_.save()

    def _log_scraping_error(self, e: Exception) -> None:
        """Log an error, passing in an error instance, e

        Args:
            e: Exception instance
        """
        L = Log()
        L.when = _stringslib.pretty_date_now(with_time=True)
        L.monitorid = self.monitorid  # noqa
        L.level = EnumLogLevel.ERROR.value
        L.action = self.parser  # noqa
        L.comment = 'Error while scraping "%s". The error was:\n%s' % (self.url, repr(e))  # noqa
        L.save()

    def _match(self, s: str):
        and_ = all([match.lower() in s.lower() for match in self._match_and_tuple]) or not self._match_and_tuple
        or_ = any([match.lower() in s.lower() for match in self._match_and_tuple]) or not self._match_or_tuple
        return and_ and or_
        # endregion instance methods

    # region instance properties
    @property
    def _match_and_tuple(self):
        if not self.match_and:  # noqa
            return tuple()
        if isinstance(self.match_and, str):  # noqa
            s = "['%s']" % self.match_and  # noqa
        else:
            s = self.match_or  # noqa
        return _ast.literal_eval(s)  # noqa

    @property
    def _match_or_tuple(self):
        if not self.match_or:  # noqa
            return tuple()
        if isinstance(self.match_or, str):  # noqa
            s = "['%s']" % self.match_or  # noqa
        else:
            s = self.match_or  # noqa
        return _ast.literal_eval(s)  # noqa

    @property
    def site(self) -> str:
        """Get the site address from the monitor url"""
        return _urlparse(self.Monitor.url).netloc  # noqa

    # endregion instance properties

    @property
    def soups(self) -> list[str]:  # noqa
        """Monitor pages frequently have additional paginated product pages
        we need to get those pages so we can soupify them to extract our products
        """
        pass


class LogExt(Log):
    class Meta:
        table_name = 'log'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class MonitorHistoryExt(MonitorHistory):
    class Meta:
        table_name = 'monitor_history'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @property
    def alert_required(self) -> bool:
        """
        Should the record generate an alert

        Returns:
            True if record generates an alert, False otherwise
        """
        # Global check for alert toggle at monitor level
        if not Monitor.get_by_id(self.monitorid).alert_required: return False
        if self.alert_sent: return False
        try:
            _ = Alert.get(Alert.price == self.price, Alert.product_title == self.product_title, Alert.monitorid == self.monitorid)
            return False
        except DoesNotExist:
            return True

    @property
    def alert_text(self) -> str:
        """Generate text for an alert for current instance"""
        M = Monitor.get_by_id(self.monitorid)
        # P = Product.get_by_id(M.productid)
        s = f'{self.date_when[0:14]} {M.supplier} {self.product_title} £{self.price}\n{self.product_url}\n'
        return s
    # endregion instance properties


class AlertExt(Alert):
    class Meta:
        table_name = 'alert'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    # region static methods
    @staticmethod
    def alerts() -> list[MonitorHistoryExt]:
        """Generate a list of monitorhistory instances that require alerting
        Note that monitorhistory table only includes rows where the price threshold
        has been met, hence no filtering on this is required (currently)
        """
        alerts = []
        histories = MonitorHistoryExt.select().where(alert_sent=0)
        h: MonitorHistoryExt
        for h in histories:
            if not h.alert_sent:
                alerts += [h]
        return alerts

    @staticmethod
    def alerts_send(carriers=[EnumAlertCarriers.PushBullet.value]):  # noqa
        """Send alerts"""
        alerts_ = AlertExt.alerts()
        body = '\n'.join([h.alert_text for h in alerts_])
        title = 'Price Alerts %s' % _stringslib.pretty_date_now(with_time=True)
        if 'PushBullet' in carriers:
            _PushBullet.send(title, body)

        if 'WhatsApp' in carriers:
            _WhatsApp.send(body)

        h: MonitorHistoryExt
        for h in alerts_:
            h.alert_sent = 1
            h.save()
    # endregion static methods


class ProductExt(Product):
    class Meta:
        table_name = 'product'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


# region monitors
class Argos(MonitorBaseMixin, Monitor):
    # This has to go here, it doesnt work in the MonitorBaseMixin
    # TODO: Test Argos
    class Meta:
        table_name = 'monitor'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)  # first to the mixin, the mixin then passes to orm.Monitor constructor

    def scrape(self):  # noqa
        self._log_scrape_started()
        try:
            for soup in self.soups:
                products = soup.find_all('div', 'ProductCardstyles__Wrapper-h52kot-1 dWoMVd StyledProductCard-sc-1o1topz-0 fOIrbR')  # noqa
                for product in products:
                    # incase website inconsistent
                    s = str(product).lower()
                    if self._match(s) and 'add to trolley' in s:  # today is in stock test
                        element = product.find('div', 'ProductCardstyles__PriceText-h52kot-17 kpmggk'.lower())  # noqa
                        price = element.strong.text
                        price = float(price.replace('£', ''))

                        element = product.find('a', 'ProductCardstyles__Link-h52kot-14 iGahUl'.lower())  # noqa
                        element = element.find('a')
                        product_url = element['href']
                        product_url = f'{self.site}{product_url}'

                        element = product.find('div', 'ProductCardstyles__Title-h52kot-13 eSMKzA'.lower())
                        product_title = element.text
                        super().scrape(price, product_url, product_title)
        except Exception as e:
            self._log_scraping_error(e)
            return
        self._log_scrape_complete()

    @property
    def soups(self) -> list[str]:
        if self._soups: return self._soups

        page_urls = [self.url]
        res = _selenium_to_str(self.url)
        soup = BeautifulSoup(res, "html.parser")
        soups = [soup]

        elements = soup.find_all('a', 'Paginationstyles__PageLink-sc-1temk9l-1 ifyeGc xs-hidden sm-row')  # noqa
        if elements:
            s = '/' if self.url[-1] == '/' else ''
            try:
                _ = elements[0]['href']
                page_urls.extend([f'{self.url}{s}{element.a['href']}' for element in elements])
            except KeyError:  # not enough products to require pagination
                pass

        page_urls = list(set(page_urls))  # we don't need the first page, we already have the soup
        if len(page_urls) > 1:
            for url in page_urls[1:]:
                _sleep(_random.randrange(1, 5))
                soups += [BeautifulSoup(_selenium_to_str(url), 'html.parser')]

        self._soups = soups
        return soups


class AWDIT(MonitorBaseMixin, Monitor):
    # This has to go here, it doesnt work in the MonitorBaseMixin
    # TODO: Test AWDIT
    class Meta:
        table_name = 'monitor'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)  # first to the mixin, the mixin then passes to orm.Monitor constructor

    def scrape(self):  # noqa
        self._log_scrape_started()
        try:
            for soup in self.soups:
                products = soup.find_all('div', 'product details product-item-details')  # noqa
                for product in products:
                    s = str(product).lower()
                    if self._match(s) and 'in stock' in s:
                        soup_tmp = BeautifulSoup(str(product.span.span), 'html.parser')
                        tag = soup_tmp.find('span', 'price-wrapper price-including-tax')  # noqa
                        price = float(tag['data-price-amount'])
                        product_url = product.a['href']  # lucky its this simple
                        product_title = product.a.text
                        super().scrape(price, product_url, product_title)
        except Exception as e:
            self._log_scraping_error(e)
            return
        self._log_scrape_complete()

    @property
    def soups(self) -> list[str]:
        if self._soups: return self._soups
        page_urls = [self.url]
        res = _selenium_to_str(self.url)
        soup = BeautifulSoup(res, "html.parser")

        anchors = soup.find_all('a', 'page')  # noqa
        if anchors:
            for tag in anchors:
                page_urls += [tag.get('href')]
            page_urls = list(set(page_urls))  # we don't need the first page, we already have the soup

        soups = [soup]
        if len(page_urls) > 1:
            for link in page_urls[1:]:
                _sleep(_random.randrange(1, 5))
                soups += [BeautifulSoup(_selenium_to_str(link), 'html.parser')]
        self._soups = soups
        return soups


class Box(MonitorBaseMixin, Monitor):
    # This has to go here, it doesnt work in the MonitorBaseMixin
    # TODO: Test Box
    class Meta:
        table_name = 'monitor'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)  # first to the mixin, the mixin then passes to orm.Monitor constructor

    def scrape(self):  # noqa
        self._log_scrape_started()
        try:
            for soup in self.soups:
                products = soup.find_all('div', 'grid grid-cols-12 gap-x-5 2xl:gap-x-[4.12rem] h-full')  # noqa
                for product in products:
                    s = str(product).lower()
                    if self._match(s) and 'add to basket' in s:  # today is in stock test
                        element = product.find('span', 'text-3xl text-heading_primary font-semibold'.lower())  # noqa
                        price = element.text
                        price = float(price.replace('£', ''))

                        element = product.find('a', 'xl:text-[18px] leading-6 text-sm font-semibold max-h-[76px] min-h-[68px] text-left no-underline block line-clamp-3'.lower())  # noqa
                        product_url = element['href']
                        product_url = f'{self.site}{product_url}'
                        product_title = element.text
                        super().scrape(price, product_url, product_title)
        except Exception as e:
            self._log_scraping_error(e)
            return
        self._log_scrape_complete()

    @property
    def soups(self) -> list[BeautifulSoup]:
        if self._soups: return self._soups

        # hack that currently works
        if 'product_list_limit' not in self.url:
            if self.url[-1] == '/':
                self.url = self.url[0:len(self.url) - 1] + '?product_list_limit=1000'
            else:
                self.url += '?product_list_limit=1000'

        res = _selenium_to_str(self.url)
        soup = BeautifulSoup(res, "html.parser")
        soups = [soup]

        self._soups = soups
        return soups


class CashConverters(MonitorBaseMixin, Monitor):
    # This has to go here, it doesnt work in the MonitorBaseMixin
    # TODO: Test CashConverters
    class Meta:
        table_name = 'monitor'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)  # first to the mixin, the mixin then passes to orm.Monitor constructor

    def scrape(self):  # noqa
        self._log_scrape_started()
        try:
            for soup in self.soups:
                products = soup.find_all('div', 'product-item__body')  # noqa
                for product in products:
                    s = str(product).lower()
                    if self._match(s):  # no instock test needed
                        element = product.find('div', 'product-item__price'.lower())  # noqa
                        price = int(element.text) + 0.99  # This is correct, we first get the pounds without the pence, then all CC items end in 99 pence, so this simple kludge works currently

                        element = product.find('span', 'product-item__text-wrapper'.lower())  # noqa
                        element = element.find('a')
                        product_url = element['href']
                        product_url = f'{self.site}{product_url}'

                        element = product.find('span', 'product-item__title__description'.lower())  # noqa
                        product_title = element.text
                        super().scrape(price, product_url, product_title)
        except Exception as e:
            self._log_scraping_error(e)
            return
        self._log_scrape_complete()

    @property
    def soups(self) -> list[BeautifulSoup]:
        ITEMS_PER_PAGE = 24
        if self._soups: return self._soups

        res = _selenium_to_str(self.url)
        soup = BeautifulSoup(res, "html.parser")
        soups = [soup]

        # now get number of pages
        element = soup.find('span', 'result-count__text')  # noqa
        page_count = int(_stringslib.numbers_in_str(element.text)[0] / ITEMS_PER_PAGE)
        # cashconverters is weird - if we put the max page count in, we dont get the last page
        # we get the entire list of items loaded, so we dont need to generate soups for each page
        # just load the last page and replace the original soup
        if page_count > 1:
            # https://www.cashconverters.co.uk/search-results?Sort=default&page=1&f%5Bcategory%5D%5B0%5D=all&f%5Blocations%5D%5B0%5D=all&query=9060
            # we need to get the page= bit from the url to replace it
            if '&page=' in self.url:
                start = self.url.index('&page=') + len('&page=')
                end = start
                while True:
                    if _stringslib.numbers_in_str(element.text[end]):
                        end += 1
                    else:
                        break
                page_url = self.url.replace(self.url[start:end], f'&page={page_count}')
                soups = [BeautifulSoup(_selenium_to_str(page_url), 'html.parser')]
            else:  # easy, no page= in the scrape url to replace
                page_url = '&page=' + str(page_count)
                # This is correct, replace the original soup with this soup that will contain every single paginated item
                soups = [BeautifulSoup(_selenium_to_str(page_url), 'html.parser')]

        self._soups = soups
        return soups


class CCLOnline(MonitorBaseMixin, Monitor):
    # This has to go here, it doesnt work in the MonitorBaseMixin
    # TODO: Test CCLOnline
    class Meta:
        table_name = 'monitor'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)  # first to the mixin, the mixin then passes to orm.Monitor constructor

    def scrape(self):  # noqa
        self._log_scrape_started()
        try:
            for soup in self.soups:
                products = soup.find_all('div', 'productlistoverlaywrapper position-relative col-12 col-xs-6 col-sm-6 col-md-4 px-2 px-xs-0 px-sm-2')  # noqa
                for product in products:
                    s = str(product).lower()
                    if self._match(s) and 'today' in s:  # today is in stock test
                        spans = product.find('p', 'order-xs-2').find_all('span')  # noqa
                        price = float(f'{spans[1].text}{spans[2].text}')  # yes, the price is weirdly split into 2 spans
                        product_url = f'{self.site}{product.a['href']}'  # lucky its this simple
                        element = product.find('h3', 'product-name text-center')  # noqa
                        product_title = element.a['title'] if element else ''
                        super().scrape(price, product_url, product_title)
        except Exception as e:
            self._log_scraping_error(e)
            return
        self._log_scrape_complete()

    @property
    def soups(self) -> list[str]:
        if self._soups: return self._soups

        page_urls = [self.url]
        res = _selenium_to_str(self.url)
        soup = BeautifulSoup(res, "html.parser")
        soups = [soup]

        listitems = soup.find_all('li', 'notselected')  # noqa
        if listitems:
            page_urls.extend([f'{self.site}{li.a['href']}' for li in listitems if 'cclonline' not in li])
            page_urls = list(set(page_urls))  # we don't need the first page, we already have the soup
            if len(page_urls) > 1:
                for url in page_urls[1:]:
                    _sleep(_random.randrange(1, 5))
                    soups += [BeautifulSoup(_selenium_to_str(url), 'html.parser')]

        self._soups = soups
        return soups


class Cex(MonitorBaseMixin, Monitor):
    """ Cex multi product scraper.

    Cex has a really shit search facility, but it mostly uses url query strings to persist searches,
    so make sure we use a decent selection of filters to minimise the number of returned products.

    Dont forget to include the in-stock filter.
    """

    # This has to go here, it doesnt work in the MonitorBaseMixin
    # TODO: Test Cex
    class Meta:
        table_name = 'monitor'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)  # first to the mixin, the mixin then passes to orm.Monitor constructor

    def scrape(self):  # noqa
        self._log_scrape_started()
        try:
            for soup in self.soups:
                products = soup.find_all('div', 'search-product-card')  # noqa
                for product in products:
                    s = str(product).lower()
                    if self._match(s) and 'in stock' in s:
                        element = product.find('p', 'product-main-price')  # noqa
                        price = _stringslib.numbers_in_str(element.text, type_=float)[0]  # noqa

                        element = element.find('a', 'line-clamp')
                        product_url = element['href']
                        product_url = f'{self.site}{product_url}'

                        product_title = element.text
                        super().scrape(price, product_url, product_title)
        except Exception as e:
            self._log_scraping_error(e)
            return
        self._log_scrape_complete()

    @property
    def soups(self) -> list[str]:
        if self._soups: return self._soups
        page_urls = [self.url]
        res = _selenium_to_str(self.url)
        soup = BeautifulSoup(res, "html.parser")

        anchors = soup.find_all('a', 'ais-Pagination-link')  # noqa
        if anchors:
            for tag in anchors:
                page_urls += [tag.get('href')]
            page_urls = list(set(page_urls))  # we don't need the first page, we already have the soup

        soups = [soup]
        if len(page_urls) > 1:
            for link in page_urls[1:]:
                _sleep(_random.randrange(1, 5))
                soups += [BeautifulSoup(_selenium_to_str(link), 'html.parser')]
        self._soups = soups
        return soups


class ComputerOrbit(MonitorBaseMixin, Monitor):
    # This has to go here, it doesnt work in the MonitorBaseMixin
    # TODO: Test ComputerOrbit
    class Meta:
        table_name = 'monitor'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)  # first to the mixin, the mixin then passes to orm.Monitor constructor

    def scrape(self):  # noqa
        self._log_scrape_started()
        try:
            for soup in self.soups:
                products = soup.find_all('div', 'productitem')  # noqa
                for product in products:
                    s = str(product).lower()
                    if self._match(s) and 'in stock' in s:  # today is in stock test
                        element = product.find('span', 'money'.lower())  # noqa
                        price = element.text
                        price = float(price.replace('£', ''))

                        element = product.find('h2', 'productitem--title'.lower())  # noqa
                        element = element.find('a')
                        product_url = element['href']
                        product_url = f'{self.site}{product_url}'

                        element = product.find('h2', 'productitem--title'.lower())
                        product_title = element.a.text
                        super().scrape(price, product_url, product_title)
        except Exception as e:
            self._log_scraping_error(e)
            return
        self._log_scrape_complete()

    @property
    def soups(self) -> list[str]:
        if self._soups: return self._soups

        page_urls = [self.url]
        res = _selenium_to_str(self.url)
        soup = BeautifulSoup(res, "html.parser")
        soups = [soup]

        elements = soup.find_all('a', 'pagination--item')  # noqa
        if elements:
            s = '/' if self.url[-1] == '/' else ''
            try:
                _ = elements[0]['href']
                page_urls.extend([f'{self.url}{s}{element.a['href']}' for element in elements])
            except KeyError:  # not enough products to require pagination
                pass

        page_urls = list(set(page_urls))  # we don't need the first page, we already have the soup
        if len(page_urls) > 1:
            for url in page_urls[1:]:
                _sleep(_random.randrange(1, 5))
                soups += [BeautifulSoup(_selenium_to_str(url), 'html.parser')]

        self._soups = soups
        return soups


class Currys(MonitorBaseMixin, Monitor):
    # This has to go here, it doesnt work in the MonitorBaseMixin
    # TODO: Test Currys
    class Meta:
        table_name = 'monitor'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)  # first to the mixin, the mixin then passes to orm.Monitor constructor

    def scrape(self):  # noqa
        self._log_scrape_started()
        try:
            for soup in self.soups:
                products = soup.find_all('div', 'row plp-list-grid')  # noqa
                for product in products:
                    # incase website inconsistent
                    s = str(product).lower()
                    if self._match(s) and 'add to basket' in s:  # today is in stock test
                        element = product.find('span', 'value'.lower())  # noqa
                        price = float(element['content'])

                        element = product.find('a', 'link text-truncate pdpLink'.lower())  # noqa
                        product_url = element['href']
                        product_url = f'{self.site}{product_url}'

                        element = product.find('h2', 'pdp-grid-product-name')
                        product_title = element.text
                        super().scrape(price, product_url, product_title)
        except Exception as e:
            self._log_scraping_error(e)
            return
        self._log_scrape_complete()

    @property
    def soups(self) -> list[str]:
        if self._soups: return self._soups

        page_urls = [self.url]
        res = _selenium_to_str(self.url)
        soup = BeautifulSoup(res, "html.parser")
        soups = [soup]

        # currys does not show every page if lots of pages, we have to construct hidden links
        # it is also in the middle of a site revision. Dont expect these hidden page
        # links to work for very long
        elements = soup.find_all('li', 'page-item')  # noqa
        if elements:
            tmp_url = self.url[0:len(self.url) - 1] if self.url[-1] == '/' else self.url
            element = soup.find('div', 'page-result-count')  # noqa
            if element:
                item_count = _stringslib.numbers_in_str(element.text)[0]
                pages = (item_count // 20) + 1  # 20 items per page default

                if pages > 1:
                    # https://www.currys.co.uk/computing/components-and-upgrades/graphics-cards?start=160&sz=20 [page 9]
                    for page in range(2, pages + 1):
                        start = page * 20 - 20
                        page_urls += [f'{tmp_url}?start={start}&sz=20']

        page_urls = list(set(page_urls))  # we don't need the first page, we already have the soup
        if len(page_urls) > 1:
            for url in page_urls[1:]:
                _sleep(_random.randrange(1, 5))
                soups += [BeautifulSoup(_selenium_to_str(url), 'html.parser')]

        self._soups = soups
        return soups


class Novatech(MonitorBaseMixin, Monitor):
    # This has to go here, it doesnt work in the MonitorBaseMixin
    # TODO: Test Novatech
    class Meta:
        table_name = 'monitor'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)  # first to the mixin, the mixin then passes to orm.Monitor constructor

    def scrape(self):  # noqa
        self._log_scrape_started()
        try:
            for soup in self.soups:
                products = soup.find_all('div', 'search-box-liner search-box-results search-hover')  # noqa
                for product in products:
                    s = str(product).lower()
                    if self._match(s) and 'left in stock' in s:  # today is in stock test
                        element = product.find('p', 'newspec-price-listing')  # noqa
                        price = _stringslib.numbers_in_str(element.text, type_=float)[0]  # noqa

                        element = product.find('div', 'search-box-details-sizer')  # noqa
                        element = element.find('a')
                        product_url = element['href']
                        product_url = f'{self.site}{product_url}'
                        product_title = element.text
                        super().scrape(price, product_url, product_title)
        except Exception as e:
            self._log_scraping_error(e)
            return
        self._log_scrape_complete()

    @property
    def soups(self) -> list[str]:
        if self._soups: return self._soups

        page_urls = [self.url]
        res = _selenium_to_str(self.url)
        soup = BeautifulSoup(res, "html.parser")

        elements = soup.find_all('div', {'id': 'page-numbers'})  # noqa
        if elements:
            s = '/' if self.site[-1] == '/' else ''
            try:
                _ = elements[0]['href']
                page_urls.extend([f'{self.site}{s}{element.a['href']}' for element in elements])
                page_urls = list(set(page_urls))  # we don't need the first page, we already have the soup
            except KeyError:  # not enough products to require pagination
                pass

        soups = [soup]
        if len(page_urls) > 1:
            for url in page_urls[1:]:
                soups += [BeautifulSoup(_selenium_to_str(url), 'html.parser')]

        self._soups = soups
        return soups


class Overclockers(MonitorBaseMixin, Monitor):
    # This has to go here, it doesnt work in the MonitorBaseMixin
    # TODO: Test Overclockers
    class Meta:
        table_name = 'monitor'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)  # first to the mixin, the mixin then passes to orm.Monitor constructor

    def scrape(self):  # noqa
        self._log_scrape_started()
        try:
            for soup in self.soups:
                products = soup.find_all('ck-product-box', 'custom-element ck-product-box listViewEventAdded')  # noqa
                for product in products:
                    s = str(product).lower()
                    if self._match(s) and 'in stock' in s:  # today is in stock test
                        element = product.find('span', 'price__amount')  # noqa
                        price = float(element.text.replace('£', ''))

                        element = product.find('a', 'text-inherit text-decoration-none js-gtm-product-link')  # noqa
                        product_url = f'{self.site}{element['href']}'
                        product_title = element.text
                        super().scrape(price, product_url, product_title)
        except Exception as e:
            self._log_scraping_error(e)
            return
        self._log_scrape_complete()

    @property
    def soups(self) -> list[str]:
        if self._soups: return self._soups

        page_urls = [self.url]
        res = _selenium_to_str(self.url)
        soup = BeautifulSoup(res, "html.parser")
        soups = [soup]

        elements = soup.find_all('div', {'id': 'page-numbers'})  # noqa
        if elements:
            s = '/' if self.url[-1] == '/' else ''
            try:
                _ = elements[0]['href']
                page_urls.extend([f'{self.url}{s}{element.a['href']}' for element in elements])
            except KeyError:  # not enough products to require pagination
                pass

        page_urls = list(set(page_urls))  # we don't need the first page, we already have the soup
        if len(page_urls) > 1:
            for url in page_urls[1:]:
                _sleep(_random.randrange(1, 5))
                soups += [BeautifulSoup(_selenium_to_str(url), 'html.parser')]

        self._soups = soups
        return soups


class RyobiSingleProduct(MonitorBaseMixin, Monitor):
    # This has to go here, it doesnt work in the MonitorBaseMixin
    # TODO: Test RyobiSingleProduct
    class Meta:
        table_name = 'monitor'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)  # first to the mixin, the mixin then passes to orm.Monitor constructor

    def scrape(self):  # noqa
        self._log_scrape_started()
        try:
            for soup in self.soups:
                products = soup.find_all('div', 'ProductDetailsstyles__Content-hb5d0o-1 ksUgWJ')  # noqa  Only one product, but keep same code pattern as multiproduct
                for product in products:
                    s = str(product).lower()
                    if self._match(s) and 'add to basket' in s:
                        element = product.find('span', 'ProductDetailPricestyles__Main-sc-80n9g9-3 frlOqI'.lower())  # noqa
                        element = element.find('span')
                        price = _stringslib.numbers_in_str(element.text, type_=float)[0]

                        product_url = self.url  # single product page, this is correct

                        element = product.find('h1', 'ProductDetailsstyles__Title-hb5d0o-3 dcvWgw'.lower())  # noqa
                        product_title = element.text
                        super().scrape(price, product_url, product_title)
        except Exception as e:
            self._log_scraping_error(e)
            return
        self._log_scrape_complete()

    @property
    def soups(self) -> list[BeautifulSoup]:
        if self._soups: return self._soups
        res = _selenium_to_str(self.url)
        soup = BeautifulSoup(res, "html.parser")
        soups = [soup]
        self._soups = soups
        return soups


class Scan(MonitorBaseMixin, Monitor):
    # This has to go here, it doesnt work in the MonitorBaseMixin
    # TODO: Test Scan
    class Meta:
        table_name = 'monitor'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)  # first to the mixin, the mixin then passes to orm.Monitor constructor

    def scrape(self):  # noqa
        self._log_scrape_started()
        try:
            for soup in self.soups:
                products = soup.find_all('div', 'search-box-liner search-box-results search-hover')  # noqa
                for product in products:
                    # incase website inconsistent
                    s = str(product).lower()
                    if self._match(s) and 'left in stock' in s:  # today is in stock test
                        element = product.find('p', 'newspec-price-listing')  # noqa
                        price = _stringslib.numbers_in_str(element.text, type_=float)[0]  # noqa

                        element = product.find('div', 'search-box-details-sizer')  # noqa
                        element = element.find('a')
                        product_url = element['href']
                        product_url = f'{self.site}{product_url}'
                        product_title = element.text
                        super().scrape(price, product_url, product_title)
        except Exception as e:
            self._log_scraping_error(e)
            return
        self._log_scrape_complete()

    @property
    def soups(self) -> list[str]:
        if self._soups: return self._soups

        page_urls = [self.url]
        res = _selenium_to_str(self.url)
        soup = BeautifulSoup(res, "html.parser")
        soups = [soup]

        elements = soup.find_all('div', {'id': 'page-numbers'})  # noqa
        if elements:
            s = '/' if self.url[-1] == '/' else ''
            try:
                _ = elements[0]['href']
                page_urls.extend([f'{self.url}{s}{element.a['href']}' for element in elements])
            except KeyError:  # not enough products to require pagination
                pass

        page_urls = list(set(page_urls))
        if len(page_urls) > 1:
            for url in page_urls[1:]:
                _sleep(_random.randrange(1, 5))
                soups += [BeautifulSoup(_selenium_to_str(url), 'html.parser')]

        self._soups = soups
        return soups


# endregion monitors


# region module helper methods
def _clean_str(s: str) -> str:
    s = _stringslib.filter_alphanumeric1(s, allow_cr=False, allow_lf=False,
                                         remove_double_quote=True, remove_single_quote=True, strip=True, fix_nbs=True)
    return s


def _fix_source(source):
    """Some random QOL fixes on source strings"""
    for generation in ('5', '6', '7'):
        for model in ('600', '700', '800', '900'):
            source = source.replace(f'{generation}{model} xt', f'{generation}{model}xt')

    source = source.lower().replace('9070 xt', '9070xt')
    source = source.replace('9060 xt', '9060xt')

    for generation in ('30', '40', '50', '60'):
        for model in ('50', '60', '70', '80', '90'):
            source = source.replace(f'{generation}{model} ti', f'{generation}{model}ti')
    return source


def _request_to_str(url: str) -> str:
    """
    Use simple request to get a webpage source as a string
    Converts to lower case.

    Args:
        url: The url to request

    Returns:
        source of page at url
    """
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:40.0) Gecko/20100101 Firefox/40.0",
        "Mozilla/5.0 (Windows NT 6.3; Trident/7.0; AS; en-US) like Gecko",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:72.0) Gecko/20100101 Firefox/72.0",
        "Mozilla/5.0 (Windows NT 6.1; rv:48.0) Gecko/20100101 Firefox/48.0",
        "Mozilla/5.0 (Linux; Android 9; SM-G960F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Mobile Safari/537.36",
        "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.122 Safari/537.36 Edge/80.0.361.109",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36",
        "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:60.0) Gecko/20100101 Firefox/60.0"
    ]
    headers = {
        "User-Agent": user_agents[_random.randrange(0, len(user_agents) - 1)]
    }
    req = requests.get(url, headers=headers)
    res = _fix_source(req.text)
    return res


def _selenium_to_str(url) -> str:
    """mucking around with downloading a page to get around bot detection

    Raises:
        errors.CaptchaError: If it looks like a captcha that we cannot circumvent

    Returns:
        str: the page as a string
    """
    with _SB(uc=True, test=True, incognito=True, undetectable=True, undetected=True) as sb:
        sb.uc_open_with_reconnect(url, 4)
        src = sb.get_page_source()
        if 'verify you are human' in src.lower():
            with _fuckit:
                sb.driver.uc_switch_to_frame("iframe")
                sb.driver.uc_click("span.mark")
                sb.uc_gui_click_captcha()
                _sleep(5)
                src = sb.get_page_source()
                if 'verify you are human' in src.lower():
                    raise _errors.CaptchaError(f'Could not pass captcha at "{url}"')

        # Accept Cookies
        try:
            if False:
                # Don't think this is actually needed, the whole source is still loaded
                ele = None  # noqa
                # OneTrust
                ele = sb.find_element('onetrust-accept-btn-handler', by='id')
                if ele:
                    ele.click()
                    # sb.wait_for_element_not_present(ele)  # Doesnt work as the element is still present after clicking "Accept"
                    _sleep(3)
        except:
            pass

        src = _fix_source(src)
        return src


# endregion


if __name__ == '__main__':
    pass

    if False:
        Mmain = Argos.get_by_id(2)
        Mmain.scrape()

    if False:
        Mmain = AWDIT.get_by_id(1)
        Mmain.scrape()

    if False:
        Mmain = Currys.get_by_id(3)
        Mmain.scrape()

    Mmain = RyobiSingleProduct.get_by_id(12)
    Mmain.scrape()
