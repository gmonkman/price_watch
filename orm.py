from peewee import *

import config as _config
import funclite.stringslib as _stringslib

_all_ = ['Alert', 'DATABASE', 'Log', 'Monitor', 'MonitorHistory', 'Product']

DATABASE = SqliteDatabase(_config.DB_PATH, pragmas={'foreign_keys': 1})


class BaseModel(Model):
    class Meta:
        database = DATABASE

class Product(BaseModel):
    productid = CharField(primary_key=True)  # eg Powercolor 9070 xt Reaper
    price_alert_threshold = FloatField(null=True)
    product_type = CharField(50)  # eg 9070 xt ... so we, for example, join on monitor to get the cheapest 9070 xt product

    class Meta:
        table_name = 'product'

class Monitor(BaseModel):
    monitorid = AutoField(primary_key=True)  # TEXT (8096)
    productid = ForeignKeyField(column_name='productid', field='productid', model=Product)
    supplier = CharField(50)  # TEXT (50)
    parser = CharField(50)  # TEXT (50)
    url = CharField(8096)  # TEXT (8096)
    last_run = CharField(30, null=True)  # TEXT (30)
    match_and = CharField(1024, constraints=[SQL("DEFAULT ''")])  # TEXT (1024)
    match_or = CharField(1024, constraints=[SQL("DEFAULT ''")])  # TEXT (1024)
    disable_alerts = IntegerField(constraints=[SQL("DEFAULT 0")])
    disable = IntegerField(constraints=[SQL("DEFAULT 0")])

    class Meta:
        table_name = 'monitor'

class Log(BaseModel):
    logid = AutoField(primary_key=True)
    monitorid = ForeignKeyField(column_name='monitorid', field='monitorid', model=Monitor, null=True)
    action = CharField(255)  # TEXT (255)
    when = CharField(30)  # TEXT (30)
    comment = CharField(8096)  # TEXT (8096)
    level = CharField(30)

    class Meta:
        table_name = 'log'


class MonitorHistory(BaseModel):
    monitor_historyid = AutoField(primary_key=True)
    monitorid = ForeignKeyField(column_name='monitorid', field='monitorid', model=Monitor)
    date_when = CharField(30)  # TEXT (30)
    product_title = CharField(255, constraints=[SQL("DEFAULT ''")])  # The product_title will be the cheapest variation of the product found, so the productid might be Radeon 9070 xt, but the title could be 'Gigabyte Radeon 9070 xt OC 16GB'
    product_url = CharField(8096, constraints=[SQL("DEFAULT ''")])  # TEXT (8096)
    price = FloatField()
    alert_sent = IntegerField(constraints=[SQL("DEFAULT 0")])

    class Meta:
        table_name = 'monitor_history'
        indexes = (
            (('monitorid', 'date_when'), True),
        )


class Alert(BaseModel):
    alertid = AutoField(primary_key=True)
    monitor_historyid = ForeignKeyField(column_name='monitor_historyid', field='monitor_historyid', model=MonitorHistory)
    carrier = CharField(50)
    date_sent = CharField(30)
    archived = IntegerField(constraints=[SQL("DEFAULT 0")])
    product_title = CharField(255)  # The product_title will be the cheapest variation of the product found, so the productid might be Radeon 9070 xt, but the title could be 'Gigabyte Radeon 9070 xt OC 16GB'
    price = FloatField()
    monitorid = ForeignKeyField(column_name='monitorid', field='monitorid', model=MonitorHistory)

    class Meta:
        table_name = 'alert'




class SqliteSequence(BaseModel):
    name = BareField(null=True)
    seq = BareField(null=True)

    class Meta:
        table_name = 'sqlite_sequence'
        primary_key = False




if __name__ == '__main__':
    pass