# -*- coding: utf-8 -*-
from odoo import models, fields,api


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

   
    mro_line_id = fields.Many2one('mro.order.parts.line', 'Ligne mro')

    @api.model
    def create(self, vals):
        order_line = super(PurchaseOrderLine, self).create(vals)
        order = order_line.order_id
        line_obj = self.env['fleet.vehicle.operation.report']
        line_obj.search([('parts_line_id', '=', order_line.mro_line_id.id), ('parts_line_id', '!=', False)]).unlink()
        data_achat = {
                         'nature' : 'fr',
                         'type' : 'order',
                         's_type' : 'standard',
                         'statut' : 'en_cours',
                         'libelle_operation' : order_line.name,
                         'mro_id' : order.mro_id.id,
                         'date' : order.mro_id.date_start,
                         'odometer' : order.mro_id.km_start or order.vehicle_id.odometer,
                         'fr_quantity' :order_line.product_qty,
                         'fr_ht' : order_line.product_qty * order_line.price_unit,
                         'partner_id' : order.partner_id.id,
                         'vehicle_id' : order.vehicle_id.id,
                         'purchase_line_id' :order_line.id
                    }
        if order_line.product_id.historique:  # ##SI L'ARTICLE EST PRÉVU POUR ÊTRE AJOUTÉ DANS L'HISTORIQUE
            line_obj.create(data_achat)
        return order_line

    @api.multi
    def write(self, vals):
        result = super(PurchaseOrderLine, self).write(vals)
        line_obj = self.env['fleet.vehicle.operation.report']
        for order_line in self: 
            order = order_line.order_id
            line = line_obj.search([('purchase_line_id', '=', order_line.id),
                                              ('purchase_line_id', '!=', False), ('invoice_line_id', '=', False)])
            data_achat = {
                         'nature' : 'fr',
                         'type' : 'order',
                         's_type' : 'standard',
                         'statut' : 'en_cours',
                         'libelle_operation' : order_line.name,
                         'mro_id' : order.mro_id.id,
                         'date' : order.mro_id.date_start,
                         'odometer' : order.mro_id.km_start or order.vehicle_id.odometer,
                         'fr_quantity' :order_line.product_qty,
                         'fr_ht' : order_line.product_qty * order_line.price_unit,
                         'partner_id' : order.partner_id.id,
                         'vehicle_id' : order.vehicle_id.id,
                         'purchase_line_id' :order_line.id
                    }
            line.write(data_achat)
        return result


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

   
    agence_id = fields.Many2one('agence.agence', 'Agence')
    vehicle_id = fields.Many2one('fleet.vehicle', 'Matériel')
    mro_id = fields.Many2one('mro.order', 'Opération')
    type_achat = fields.Selection([('achat', 'Achat'), ('carburant', 'Carburant'), ('vehicule', 'Véhicule'), ('remorque', 'Remorque'), ('entretien', 'Entretien'), ('assistance', 'Assistance')], 'Type achat')
    type_facture_id = fields.Many2one('account.invoice.type', "Type de facture", readonly=True, states={'draft': [('readonly', False)]})

