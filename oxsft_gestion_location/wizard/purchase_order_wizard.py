# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class PurchaseOrderWizard(models.TransientModel):
    _name = "purchase.order.wizard"
    
    @api.model
    def _get_active_id(self):
        return self.env.context.get('active_id')

    @api.model
    def _get_type_facture_id(self):
        model,type_id = self.env['ir.model.data'].get_object_reference('account','account_invoice_type_OR')
        return type_id

    type_facture_id = fields.Many2one('account.invoice.type',"Type de facture",default=_get_type_facture_id)
    mro_id = fields.Many2one('mro.order','OR',required=True,default=_get_active_id,ondelete="cascade")
    

    @api.multi
    def create_order(self):
        order_exists = False
        order_obj = self.env['purchase.order']
        order_line_obj = self.env['purchase.order.line']
        orders = []
        po_data = {}
        po_line_data =  {}
        for data in self:
            for line in data.mro_id.parts_lines:
                prev_order_line = order_line_obj.search([('mro_line_id','=',line.id)])
                if prev_order_line: ###SI LA LIGNE A DÉJÀ ÉTÉ COMMANDÉE
                    order_exists = True
                    continue
                po_data.setdefault(line.supplier_id.id, [])
                po_line_data.setdefault(line.supplier_id.id, [])
                po_data[line.supplier_id.id] =  self._get_purchase_vals(data, line.supplier_id)
                po_line = (0,0,{"mro_line_id":line.id,"date_planned":data.mro_id.date_scheduled,"name":line.parts_id.name,"product_id":line.parts_id.id,"product_uom":line.parts_uom.id,"product_qty":line.parts_qty,'price_unit':line.price_unit})
                po_line_data[line.supplier_id.id].append(po_line)
                    
            for key,purchase_data in po_data.items():
                if key == False:
                    continue
                purchase_data["order_line"] = po_line_data[key]
                purchase = order_obj.create(purchase_data)
                orders.append(purchase)
        if not orders:
            if order_exists:
                raise UserError(_("Commande(s) déjà créée(s)!"))
            raise UserError(_('Aucune commande!'))
        
        return True


    def _get_purchase_vals(self,data, supplier):
        user = self.env.user
        payment_term_id = supplier.property_supplier_payment_term_id.id or False
        return {
            "type_facture_id" : data.type_facture_id.id,
            "mro_id":data.mro_id.id,
            'vehicle_id':data.mro_id.vehicle_id.id,
            'origin': data.mro_id.name,
            #'location_id':data.mro_id.parts_location_id.id,
            'date_order': data.mro_id.date_start,
            'partner_id': supplier.id,
            'payment_term_id': payment_term_id,
            'fiscal_position_id': supplier.property_account_position_id.id,
            'company_id': user.company_id.id,
            }
