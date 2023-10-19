# -*- coding: utf-8 -*-


from odoo import models, fields, api


class VehicleCost(models.Model):
    _name = "o.table.vehicle.cost"

    @api.depends("o_TbVehicleCost_TbMroLine_id","o_TbVehicleCost_TbMroLine_id.parts_qty","o_TbVehicleCost_TbMroLine_id.price_unit")
    def  _compute_amount_total(self):
        self.o_TbVehicleCost_Total = self.o_TbVehicleCost_TbMroLine_id.amount_total
    
    o_TbVehicleCost_TbVehicle_id = fields.Many2one('fleet.vehicle',"Véhicule")
    o_TbVehicleCost_TbAgence_id = fields.Many2one('agence.agence',"Agence")
    o_TbVehicleCost_TbModel_id = fields.Many2one('fleet.vehicle.model',"Modèle")
    o_TbVehicleCost_Start_Idt = fields.Date("Date de début")
    o_ViewVehicleCost_Stop_Idt = fields.Date("Date de fin")
    o_TbVehicleCost_TbProduct_id = fields.Many2one('product.product',"Prestation")
    o_TbVehicleCost_Total = fields.Float(compute="_compute_amount_total",string="Cost",store=True)
    o_TbVehicleCost_TbMroLine_id = fields.Many2one('mro.order.parts.line', 'Ligne MRO')



class MroOrderPartsLine(models.Model):
    _inherit = 'mro.order.parts.line'

    @api.model
    def create(self, vals):
        line = super(MroOrderPartsLine,self).create(vals)
        data_cost = {
                "o_TbVehicleCost_TbVehicle_id":line.maintenance_id.vehicle_id.id,
                "o_TbVehicleCost_TbAgence_id" :line.maintenance_id.vehicle_id.agence_id.id,
                "o_TbVehicleCost_TbModel_id":line.maintenance_id.vehicle_id.model_id.id,
                "o_TbVehicleCost_Start_Idt":line.maintenance_id.date_start,
                "o_ViewVehicleCost_Stop_Idt":line.maintenance_id.date_stop,
                "o_TbVehicleCost_TbProduct_id":line.parts_id.id,
                "o_TbVehicleCost_TbMroLine_id":line.id,
            }
        self.env['o.table.vehicle.cost'].sudo().create(data_cost)
        return line

    @api.multi
    def unlink(self):
        costs = self.env['o.table.vehicle.cost'].search([('o_TbVehicleCost_TbMroLine_id','in',self.ids)])
        costs.sudo().unlink()
        return super(MroOrderPartsLine,self).unlink()

