# -*- coding: utf-8 -*-

from dateutil import tz
from odoo import fields


def formatDate(self,date_str):
    d  = fields.Date.from_string(date_str)
    return d.strftime("%d/%m/%Y")

def formatDatetime(self,datetime_str):
    dt  = fields.Datetime.from_string(datetime_str)
    return dt.strftime("%d/%m/%Y %H:%M:%S")

