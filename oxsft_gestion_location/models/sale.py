# -*- coding: utf-8 -*-
from odoo import models, fields


class SaleOrder(models.Model):
    _inherit = 'sale.order'

   
    vehicle_id = fields.Many2one('fleet.vehicle', 'Matériel')

