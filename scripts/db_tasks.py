"""Selection of scripts related to the database"""
import argparse

from orm import *
from orm_extensions import *  # noqa


def main():
    """main"""
    cmdline = argparse.ArgumentParser(description=__doc__)  # use the module __doc__

    if False:
        # named: eg script.py -part head
        cmdline.add_argument('-part', '--part', help='The region part eg. head.', required=True)

        # argument present or not: e.g. scipt.py -f
        # args.fix == True
        cmdline.add_argument('-f', '--fix', help='Fix it', action='store_true')

        # positional: e.g. scipt.py c:/temp
        # args.folder == 'c:/temp'
        cmdline.add_argument('folder', help='folder')

        # get a list from comma delimited args

        # see https://stackoverflow.com/questions/15753701/argparse-option-for-passing-a-list-as-option
        f = lambda s: [int(item) for item in s.split(',')]
        cmdline.add_argument('-l', '--list', type=f, help='delimited list input, eg -l 12,13,14')
        # mylist = args.list

        # multiple positional arguments: e.g. script.py -files_in 'c:/' 'd:/'
        # for fname in args.files_in:
        cmdline.add_argument('-i', '--files_in', help='VGG JSON files to merge', nargs='+')

    args = cmdline.parse_args()  # noqa


def data_upsert():
    """Insert data into the database"""
    _ = Product.get_or_create(productid='9070xt',
                              defaults={'price_alert_threshold': 600,
                                        'product_type': '9070xt'})

    _ = Monitor.get_or_create(productid='9070xt', match_and='9070xt', parser='AWDIT', supplier='AWDIT',
                              url='https://www.awd-it.co.uk/components/graphics-cards/radeon.html?product_list_limit=64',
                              )




if __name__ == "__main__":
    pass
    # main()
    # data_upsert()
