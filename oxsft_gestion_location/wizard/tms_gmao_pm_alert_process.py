# -*- coding: utf-8 -*-
##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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

from odoo import api, models, fields


UNITE_SELECTION = [
                   ('annee','Année'),('mois','Mois'),
                   ('days', 'Jours'),('horaire','Heure'),
                   ('km', 'Km')
                  ]

class TmsGmaoPmAlertProcess(models.TransientModel):
    u"""Traitement alerte"""
    _name = "tms.gmao.pm.alert.process"
    _description = u"Traitement alerte"

    @api.model
    def _default_user(self):
        return self.env.user.id

    @api.onchange('line_ids')
    def get_price_subtotal(self):
        amount_total = 0.0
        for line in self.line_ids:
            amount_total +=line.product_qty * line.amount
        self.amount_total = amount_total

    alert_id = fields.Many2one('tms.gmao.pm.alert',u'alerte',required=True,readonly=True,ondelete="cascade")
    vehicle_id = fields.Many2one('fleet.vehicle', u'Véhicule', readonly=True)
    periodic_done = fields.Boolean(u'Terminer la périodicité de la maintenance',default=False)
    date = fields.Datetime('Date', required=True,default=fields.Datetime.now)
    maintenancier_id = fields.Many2one('hr.employee','Opérateur')
    line_ids = fields.One2many('tms.gmao.pm.alert.process.line','process_id', 'Vidanges')
    periodic_ok = fields.Boolean('Périodique')
    meter = fields.Selection(UNITE_SELECTION, 'Unité',required=True)
    km = fields.Float('KM')
    description = fields.Char('Description', size=50)
    user_id = fields.Many2one('res.users', u'Responsable',default=_default_user)
    amount_total = fields.Float("Montant total",readonly=True)

    @api.multi
    def write(self, vals):
        for process in self:
            if vals.get('km'):
                self.env['fleet.vehicle.odometer'].create({'vehicle_id':process.vehicle_id.id,'value':vals.get('km'),'date':process.date,'origin':'alerte'})
        return super(TmsGmaoPmAlertProcess,self).write(vals)
    
    def action_done(self):
        ###"""Effectuer maintenance"""
        mro_obj = self.env['mro.order']
        for object_process in self:
            if object_process.line_ids:
                description = object_process.description
                if not description:
                    description = object_process.alert_id.name
                mro_datas={
                       'maintenance_type': 'pm',
                       'service_type_id': object_process.alert_id and object_process.alert_id.pm_id and object_process.alert_id.pm_id.service_type_id.id or False,
                       'origin': object_process.alert_id and object_process.alert_id.pm_id and object_process.alert_id.pm_id.name or "",
                       'user_id' : object_process.user_id and object_process.user_id.id or False,
                       'vehicle_id': object_process.vehicle_id and object_process.vehicle_id.id or False,
                       'description': description,
                       'date_planned': object_process.date,
                       'date_scheduled': object_process.date,
                       'date_execution': object_process.date,
                       'date_start': object_process.date,
                       'date_stop': object_process.date,
                       'alert_id': object_process.alert_id and object_process.alert_id.id or False,
                       'km_start': object_process.km or 0,
                       'maintenancier_id' : object_process.maintenancier_id and object_process.maintenancier_id.id or False,
                       }
                mros = mro_obj.search([('alert_id','=',object_process.alert_id.id)])
                if mros:
                    mro = mros[0]
                else:
                    mro = mro_obj.create(mro_datas)
                if mro:
                    amount  = 0
                    for object_process_line in object_process.line_ids:
                        parts_datas = {
                            'name' : object_process_line.description,
                            'parts_id' : object_process_line.product_id and object_process_line.product_id.id or False,
                            'parts_uom' : object_process_line.product_id and object_process_line.product_id.uom_id.id or False,
                            'price_unit' : object_process_line.amount or 0,
                            'parts_qty' : object_process_line.product_qty or 0,
                            'maintenance_id': mro.id,
                        }
                        amount += object_process_line.product_qty * object_process_line.amount
                        self.env['mro.order.parts.line'].create(parts_datas)
                    object_process.alert_id.validate_alert(not object_process.periodic_done, object_process.date, object_process.km)
                    
                    if object_process.alert_id.pm_id.pm_id:##Mettre fin à l'alerte exclusive liée
                        object_process.alert_id.pm_id.pm_id.end_pm()
                    
                    mros = mro_obj.search([('alert_id','=',object_process.alert_id.id),('state','=','draft')])
                    for mro in mros:
                        #workflow.trg_validate(self.env.user.id, "mro.order", mro.id, "button_confirm_order", self.env.cr) ++zart
                        self.env['mro.order'].browse(mro.id).button_confirm_order()
        return True

class TmsGmaoPmAlertProcessLine(models.TransientModel):
    u"""Traitement des lignes d'alerte"""
    _name = "tms.gmao.pm.alert.process.line"
    _description = u"Traitement ligne d'alerte"
    
    process_id = fields.Many2one('tms.gmao.pm.alert.process', u'Bon de maintenance')
    product_id = fields.Many2one('product.product', u'Produit', required=True)
    product_qty = fields.Float(u'Quantité')
    amount = fields.Float(u'Coût')
    description = fields.Char(u'Description', size=50)
    price_subtotal = fields.Float("Montant",readonly=True)

    @api.onchange('product_qty','amount')
    def get_price_subtotal(self):
        self.price_subtotal = self.product_qty * self.amount

    @api.onchange('product_id')
    def onchange_product_id(self):
        ###"""évènements lors du change de produit"""
        self.amount = self.product_id.standard_price

