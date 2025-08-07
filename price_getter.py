import requests
from bs4 import BeautifulSoup

PRICES_REQUESTED = 0



def get_price(link: str, parser_name: str) -> int | float | None:
    """
    Returns price of item with link of item, only works with MercadoLibre

    Parameters:
        link (str): link of the item you want to keep a hold of
        parser_name (str): name of the parser, in ['ebay', 'amazon', 'awdit_9070xt']

    Return:
        (int) currentPrice of item
    """
    global PRICES_REQUESTED

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
        "User-Agent": user_agents[PRICES_REQUESTED % len(user_agents)]
    }

    PRICES_REQUESTED += 1

    # Some links return multiple pages, we want to check the content of each page so
    # we get all the pages and check them

    soup = None
    if parser_name == 'awdit_9070xt':
        # get first page
        req = requests.get(link, headers=headers)
        res = req.text
        res = res.replace('9070 xt', '9070xt')  # yes, they have mixed names
        soup = BeautifulSoup(res, "html.parser")
        min_price = None  # awdit_9070xt(soup)
        last_page = 0

        page_urls = []
        anchors = soup.find_all('a', 'page')
        if anchors:
            for tag in anchors:
                page_urls += [tag.get('href')]
        page_urls = list(set(page_urls))
        soups = [soup]
        for url in page_urls:
            soups += BeautifulSoup(requests.get(url).text, "html.parser")

        for soup in soups:
            products = soup.find_all('div', 'product details product-item-details')  # noqa
            for product in products:
                try:
                    s = str(product).lower()
                    if ('9070xt' in s or '9070 xt' in s) and 'in stock' in s:
                        soup_tmp = BeautifulSoup(str(product.span.span), 'html.parser')
                        tag = soup_tmp.find('span', 'price-wrapper price-including-tax')   # noqa
                        price = float(tag['data-price-amount'])
                        if price:
                            min_price = price if min_price > price > 0 else min_price
                except:
                    pass

    elif parser_name == 'ebay' or parser_name == 'amazon':
        req = requests.get(link, headers=headers)
        res = req.text
        soup = BeautifulSoup(res, "html.parser")

        try:
            # TODO Sort this return
            if parser_name == 'ebay':
                return float(soup.select(".x-price-primary")[0].text.replace("£", ""))
            else:
                return float(soup.select(".aok-offscreen")[0].text.split(" ")[0].replace("£", ""))
        except:
            return -1
    return None


if __name__ == '__main__':
    get_price('https://www.awd-it.co.uk/components/graphics-cards/radeon.html?product_list_limit=64', 'awdit_9070xt')
    pass
