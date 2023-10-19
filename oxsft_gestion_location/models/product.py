# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from odoo import models, fields, api


class ProductProduct(models.Model):
    _inherit = 'product.product'

    # spare_ok = fields.Boolean(related='product_tmpl_id.spare_ok',string='Pièces de rechange')
    prestation_ok = fields.Boolean(related='product_tmpl_id.prestation_ok', string='Prestation')
    vente = fields.Boolean('Vente', help="Cochez cette case pour faire apparaitre ce type dans l'onglet vente",
                           default=True)
    achat = fields.Boolean('Achat', help="Cochez cette case pour faire apparaitre ce type dans l'onglet achat",
                           default=True)
    historique = fields.Boolean(string='Historique',
                                help="Cochez cette case pour faire apparaitre ce type dans l'historique des opérations",
                                default=True)
    prorata = fields.Boolean(string='Prorata', help="Cochez cette case pour permettre le prorata", default=True)
    type_prestation = fields.Selection([('tj', 'T+J'), ('assurance', 'Assurances')], "Type de prestation")

    @api.model
    @api.returns('self', lambda value: value.id)
    def create(self, vals):
        ctx = dict(self.env.context)
        if vals.get('spare_ok'):
            ctx['default_spare_ok'] = True
        if vals.get('prestation_ok'):
            ctx['default_prestation_ok'] = True
        self.env.context = ctx
        return super(ProductProduct, self).create(vals)

    @api.multi
    def write(self, vals):
        line_obj = self.env['fleet.vehicle.operation.report']
        result = super(ProductProduct, self).write(vals)
        if 'historique' in vals:
            line_obj.init()
        return result

    """
    @api.onchange('spare_ok')
    def onchange_spare_ok(self):
        if self.spare_ok:
            model,data_id = self.env['ir.model.data'].get_object_reference('mro','product_category_mro')
            if data_id:
                self.categ_id = data_id
    """


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # spare_ok = fields.Boolean('Pièces de rechange')
    prestation_ok = fields.Boolean('Prestation')
