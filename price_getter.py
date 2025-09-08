"""
Main work to extract prices from the various parsers.

Valid parsers are:

    awdit:
        Multiproduct parser for awdit

    cclonline:
        Multi product parser for cclonline

    ebay_single_product:
        Supports a link to a single product listing.
        Does not require config of the match_and and match_or in the DB.

    amazon_single_product:
        Supports a link to a single product listing.
        Does not require config of the match_and and match_or in the DB.
"""
import requests
from time import sleep as _sleep
import random as _random

from bs4 import BeautifulSoup
from seleniumbase import SB as _SB
import fuckit as _fuckit

import funclite.stringslib as _stringslib

import errors as _errors
# from orm import Log, Monitor  # noqa


PRICES_REQUESTED = 0


def get_price(link: str, parser: str, match_and: str | tuple = (), match_or: str | tuple = ()) -> tuple[float, str, str] | None:
    # TODO: After testing, convert this to accept an instance of Monitor. Utimately convert everything to class instances and implement get_price in each monitor class
    """
    Returns price of item with link of item

    Parameters:
        link (str): link of the item you want to keep a hold of
        parser (str): name of the parser, in ['ebay', 'amazon', 'awdit_9070xt']

        match_and (tuple, optional):
            For parsers that search multiple items, this identifies the item we want.
            The search text is set in sqlite table monitor. The product must match all

        match_or (tuple, optional):
            or match on items. At least one of match_and or match_or is required.

    Return:
        Tuple, with the price of the item or None and the url of the item.

        The url of the item can differ from the link passed to get_price where
        the link has multiple items, only one of which will be the cheapest.

        Returns None if get_price fails,
    """
    global PRICES_REQUESTED

    if isinstance(match_and, str):
        match_and = (match_and,)

    if isinstance(match_or, str):
        match_or = (match_or,)

    min_price, min_product_url, min_product_title, soup, page_urls = None, None, None, None, []

    PRICES_REQUESTED += 1

    # Some links return multiple pages, we want to check the content of each page so
    # we get all the pages and check them
    # ******************************************************************************
    # REMEMBER THAT ALL PAGE SOURCES ARE CONVERTED TO LOWER CASE BEFORE SOUPING THEM
    # ******************************************************************************
    if parser == 'awdit':  # includes clearance items, does not currently use Cloudfare
        # get first page
        res = _selenium_to_str(link)
        soup = BeautifulSoup(res, "html.parser")

        anchors = soup.find_all('a', 'page')  # noqa
        if anchors:
            for tag in anchors:
                page_urls += [tag.get('href')]
        page_urls = list(set(page_urls))  # we don't need the first page, we already have the soup

        soups = [soup]
        for url in page_urls:
            soups += [BeautifulSoup(_selenium_to_str(url))]

        for soup in soups:
            products = soup.find_all('div', 'product details product-item-details')  # noqa
            for product in products:
                try:
                    s = str(product).lower()
                    if _match(s, match_and, match_or):
                        soup_tmp = BeautifulSoup(str(product.span.span), 'html.parser')
                        tag = soup_tmp.find('span', 'price-wrapper price-including-tax')  # noqa
                        price = float(tag['data-price-amount'])
                        product_url = product.a['href']  # lucky its this simple
                        product_title = product.a.text
                        if price:
                            if (isinstance(min_price, (float, int)) and min_price > price > 0) or min_price is None:
                                min_price = price
                                min_product_url = product_url
                                min_product_title = product_title
                except:
                    pass
        return min_price, min_product_url, min_product_title
    elif parser == 'cclonline':  # protected by cloudfare
        # get first page
        site = 'https://www.cclonline.com'
        res = _selenium_to_str(link)
        soup = BeautifulSoup(res, "html.parser")

        listitems = soup.find_all('li', 'notselected')  # noqa
        page_urls = [f'{site}{li.a['href']}' for li in listitems if 'cclonline' not in li]
        page_urls = list(set(page_urls))  # we don't need the first page, we already have the soup
        soups = [soup]
        for url in page_urls:
            soups += [BeautifulSoup(_selenium_to_str(url))]

        for soup in soups:
            products = soup.find_all('div', 'productlistoverlaywrapper position-relative col-12 col-xs-6 col-sm-6 col-md-4 px-2 px-xs-0 px-sm-2')  # noqa
            for product in products:
                try:
                    # incase website inconsistent
                    s = str(product).lower()
                    if _match(s, match_and, match_or) and 'today' in s:  # today is in stock test
                        spans = product.find('p', 'order-xs-2').find_all('span')  # noqa
                        price = float(f'{spans[1].text}{spans[2].text}')  # yes, the price is weirdly split into 2 spans
                        product_url = f'{site}{product.a['href']}'  # lucky its this simple
                        element = product.find('h3', 'product-name text-center')  # noqa
                        product_title = element.a['title'] if element else ''

                        if price:
                            if (isinstance(min_price, (float, int)) and min_price > price > 0) or min_price is None:
                                min_price = price
                                min_product_url = product_url
                                min_product_title = product_title
                except:
                    pass
        return min_price, min_product_url, min_product_title
    elif parser == 'novatech':
        # get first page
        # TODO: Debug novatech
        site = 'https://www.novatech.co.uk'
        res = _selenium_to_str(link)
        soup = BeautifulSoup(res, "html.parser")

        elements = soup.find_all('div', {'id': 'page-numbers'})  # noqa
        if elements:
            s = '/' if link[-1] == '/' else ''
            try:
                _ = elements[0]['href']
                page_urls = [f'{link}{s}{element.a['href']}' for element in elements]
            except KeyError:  # not enough products to require pagination
                pass

        page_urls = list(set(page_urls))  # we don't need the first page, we already have the soup
        soups = [soup]
        for url in page_urls:
            soups += [BeautifulSoup(_selenium_to_str(url))]

        for soup in soups:
            products = soup.find_all('div', 'search-box-liner search-box-results search-hover')  # noqa
            for product in products:
                try:
                    # incase website inconsistent
                    s = str(product).lower()
                    price, product_url = None, ''
                    if _match(s, match_and, match_or) and 'left in stock' in s:  # today is in stock test
                        element = product.find('p', 'newspec-price-listing')  # noqa
                        price = _stringslib.numbers_in_str(element.text, type_=float)[0]  # noqa

                        element = product.find('div', 'search-box-details-sizer')  # noqa
                        element = element.find('a')
                        product_url = element['href']
                        product_url = f'{site}{product_url}'
                        product_title = element.text

                        if price:
                            if (isinstance(min_price, (float, int)) and min_price > price > 0) or min_price is None:
                                min_price = price
                                min_product_url = product_url
                                min_product_title = product_title
                except:
                    pass
        return min_price, min_product_url, min_product_title
    elif parser == 'overclockers':
        # get first page
        # TODO: Debug overclockers
        site = 'https://www.overclockers.co.uk'
        res = _selenium_to_str(link)
        soup = BeautifulSoup(res, "html.parser")

        elements = soup.find_all('a', 'page-link pagination__step')  # noqa
        if elements:
            page_urls = [f'{site}{element['href']}' for element in elements]
            page_urls = list(set(page_urls))  # we don't need the first page, we already have the soup

        soups = [soup]
        for url in page_urls:
            soups += [BeautifulSoup(_selenium_to_str(url))]

        for soup in soups:
            products = soup.find_all('ck-product-box', 'custom-element ck-product-box listViewEventAdded')  # noqa
            for product in products:
                try:
                    # incase website inconsistent
                    s = str(product).lower()
                    price, product_url = None, ''
                    if _match(s, match_and, match_or) and 'in stock' in s:  # today is in stock test
                        element = product.find('span', 'price__amount')  # noqa
                        price = float(element.text.replace('£', ''))

                        element = product.find('a', 'text-inherit text-decoration-none js-gtm-product-link')  # noqa
                        product_url = f'{site}{element['href']}'
                        product_title = element.text

                        if price:
                            if (isinstance(min_price, (float, int)) and min_price > price > 0) or min_price is None:
                                min_price = price
                                min_product_url = product_url
                                min_product_title = product_title
                except:
                    pass
        return min_price, min_product_url, min_product_title
    elif parser == 'scan':
        # Scan differs from most other sites ...
        # You have to drill into the items you want, then it displays everything
        # on a single page with no paginated results
        # TODO: Debug Scan
        site = 'https://www.scan.co.uk'
        res = _selenium_to_str(link)
        soup = BeautifulSoup(res, "html.parser")

        products = soup.find_all('li', 'product')  # noqa
        for product in products:
            try:
                # incase website inconsistent
                s = str(product).lower()
                price, product_url = None, ''
                if _match(s, match_and, match_or) and 'in stock' in s:  # today is in stock test
                    element = product.find('span', 'price')  # noqa
                    pounds = float(element.text)
                    pence = float(element.find_all('small')[1].text)
                    price = pounds + (pence/100)

                    element = product.find('span', 'description').a  # noqa
                    product_url = f'{site}{element['href']}'
                    product_title = element.text

                    if price:
                        if (isinstance(min_price, (float, int)) and min_price > price > 0) or min_price is None:
                            min_price = price
                            min_product_url = product_url
                            min_product_title = product_title
            except:
                pass
        return min_price, min_product_url, min_product_title
    elif parser == 'ebay_single_product' or parser == 'amazon_single_product':
        res = _request_to_str(link)
        soup = BeautifulSoup(res, "html.parser")

        try:
            if parser == 'ebay':

                return float(soup.select(".x-price-primary")[0].text.replace("£", "")), link, ''
            else:
                return float(soup.select(".aok-offscreen")[0].text.split(" ")[0].replace("£", "")), link, ''
        except:
            return None
    else:
        print('** Unrecognized parser passed to get_price **')
    return None


def _match(s: str, match_and: tuple, match_or: tuple):
    and_ = all([match.lower() in s.lower() for match in match_and]) or not match_and
    or_ = any([match.lower() in s.lower() for match in match_and]) or not match_or
    return and_ and or_


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
                ele = None
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



def _fix_source(source):
    """Some random QOL fixes on source strings"""
    source = source.lower().replace('9070 xt', '9070xt')
    source = source.replace('9060 xt', '9060xt')
    return source


if __name__ == '__main__':
    pass
    # get_price('https://www.awd-it.co.uk/components/graphics-cards/radeon.html?product_list_limit=64', 'awdit', '9070xt')
    # get_price('https://www.cclonline.com/pc-components/graphics-cards/', 'cclonline', match_and=('9070xt',))
    # get_price('https://www.novatech.co.uk/products/components/amdradeongraphicscards/', 'novatech', match_and=('9070xt',))




    # _selenium_to_str('https://www.cclonline.com/pc-components/graphics-cards/')

    pass
