# -*- coding: utf-8 -*-
from dateutil import relativedelta

from odoo import models, fields, api


class FleetVehicleContractPeriod(models.Model):
    _name = "fleet.vehicle.contract.period"
    
    code = fields.Char('Code', required=True)
    name = fields.Char('Period Name', required=True)
    date_start = fields.Date('Start of Period', required=True)
    date_stop = fields.Date('End of Period', required=True)

    _order = "date_start desc"
    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'The name of the period must be unique!'),
        ('code_uniq', 'unique(code)', 'The name of the period must be unique!'),
    ]
    @api.multi
    def _check_duration(self):
        self.ensure_one()
        obj_period = self
        if obj_period.date_stop < obj_period.date_start:
            return False
        return True


    _constraints = [
        (_check_duration, 'Error!\nThe duration of the Period(s) is/are invalid.', ['date_stop']),
    ]

    @api.multi
    @api.returns('self')
    def find(self,dt=None):
        if not dt:
            dt = fields.Date.context_today(self)
        args = [('date_start', '<=' ,dt), ('date_stop', '>=', dt)]
        result = self.search(args)
        if not result:
            result = self.create_period(dt)
        return result

    @api.multi
    def create_period(self,dt,interval=1):
        dt_string =  dt
        if not isinstance(dt, str):
            dt_string = fields.Date.to_string(dt)
        dt_string_split = dt_string.split("-")
        dt_string_split[2]  = 1
        dt_string = str(dt_string_split[0])+"-"+str(dt_string_split[1])+"-"+str(dt_string_split[2])
        ds = fields.Date.from_string(dt_string)
        contract_period_obj = self.env['fleet.vehicle.contract.period']
        de = ds + relativedelta.relativedelta(months=interval, days=-1)


        return contract_period_obj.create({
                    'name': ds.strftime('%m/%Y'),
                    'code': ds.strftime('%m/%Y'),
                    'date_start': ds.strftime('%Y-%m-%d'),
                    'date_stop': de.strftime('%Y-%m-%d'),
                })


