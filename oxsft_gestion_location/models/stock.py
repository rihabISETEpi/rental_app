# -*- coding: utf-8 -*-
from odoo import models, fields, api


class StockMove(models.Model):
    _inherit = 'stock.move'

   
    mro_line_id = fields.Many2one('mro.order.parts.line', 'Ligne de maintenance')
    mro_id = fields.Many2one('mro.order',related="mro_line_id.maintenance_id",string='Maintenance')
    product_qty_available = fields.Float(related='product_id.qty_available',string='Quantité en stock',readonly=True)


    @api.model
    def create(self, vals):
        move = super(StockMove,self).create(vals)
        move.get_move_write()
        return move

    
    @api.multi
    def write(self, vals):
        res = super(StockMove,self).write(vals)
        if 'picking_id' in vals:
            for move in self:
                move.get_move_write()  ## CETTE FONCTION
        return res

    @api.onchange('product_id')
    def onchange_product_id(self):
        product = self.product_id.with_context(lang=self.partner_id.lang or self.env.user.lang)
        self.product_qty_available = product.qty_available
        return super(StockMove,self).onchange_product_id()

    @api.multi
    def get_move_write(self):
        self.ensure_one()
        move = self
        if move.purchase_line_id.mro_line_id:
            move.write({'mro_line_id':move.purchase_line_id.mro_line_id.id})
        
        if move.procurement_id.sale_line_id:
            move.picking_id.write({
                        'vehicle_id':move.procurement_id.sale_line_id.order_id.vehicle_id.id
                       }) 
        elif move.purchase_line_id:
            move.picking_id.write({
                        'vehicle_id':move.purchase_line_id.order_id.vehicle_id.id,
                        'mro_id':move.purchase_line_id.order_id.mro_id.id,
                        'type_achat':move.purchase_line_id.order_id.type_achat,
                        'type_facture_id':move.purchase_line_id.order_id.type_facture_id.id,
                        'agence_id':move.purchase_line_id.order_id.agence_id.id,
                       })
        elif move.group_id.vehicle_id and not move.picking_id.vehicle_id:
            move.picking_id.write({'vehicle_id':move.group_id.vehicle_id.id})

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    agence_id = fields.Many2one('agence.agence', 'Agence')
    vehicle_id  = fields.Many2one('fleet.vehicle', 'Matériel')
    mro_id = fields.Many2one('mro.order', 'Opération')
    type_achat = fields.Selection([('achat', 'Achat'), ('carburant', 'Carburant'), ('vehicule', 'Véhicule'), ('remorque', 'Remorque'), ('entretien', 'Entretien'), ('assistance', 'Assistance')], 'Type achat')
    type_facture_id = fields.Many2one('account.invoice.type', "Type de facture", readonly=True, states={'draft': [('readonly', False)]})


class ProcurementGroup(models.Model):
    """ Procurement Group """
    _inherit = "procurement.group"
    
    vehicle_id = fields.Many2one('fleet.vehicle','Véhicule')  ###CECI A ÉTÉ AJOUTÉ POUR LE MODULE MRO.

    







    