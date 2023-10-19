# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class account_invoice(models.Model):
    _inherit = "account.invoice"
    
    related_invoice_id = fields.Many2one('account.invoice','Facture origine(Refacturation)')

class account_invoice_wizard2(models.TransientModel):
    _name = "account.invoice.wizard2"
    
    @api.model
    def _get_journal(self):
        journal_obj = self.env['account.journal']
        journals = journal_obj.search([('type', '=', "sale")])
        return journals and journals[0].id or False
    
    @api.model
    def _get_active_id(self):
        return self.env.context.get('active_id')

    @api.model
    def _get_partner_id(self):
        model,type_id = self.env['ir.model.data'].get_object_reference('base','res_partner_divers')
        return type_id

    
    partner_id = fields.Many2one('res.partner',"Client",default=_get_partner_id,required=True,ondelete="cascade")
    invoice_id = fields.Many2one('account.invoice','Facture',default=_get_active_id,required=True,ondelete="cascade")

    journal_id = fields.Many2one('account.journal', 'Destination Journal',default=_get_journal,required=True,ondelete="cascade")


    @api.multi
    def create_invoice(self):
        invoice_obj = self.env['account.invoice']
        invoices = []
        invoice_data = {}
        invoice_line_data =  []
        for data in self:
            date_invoice = data.invoice_id.date_invoice2
            invoice_data =  self._get_invoice_vals(data, data.partner_id, "out_invoice", data.journal_id.id,date_invoice)
            for line in data.invoice_id.invoice_line_ids:
                invoice_line_tax_ids =[]
                for tax in line.invoice_line_tax_ids:
                    sale_tax_id = False
                    self.env.cr.execute("""select id from account_tax where type_tax_use='sale' and
                                        price_include=%s and amount_type=%s and @ (amount-%s) < 0.01
                                        """,(tax.price_include,tax.amount_type,tax.amount,)) ####RECUPERER LA TAXE EQUIVALENTE POUR LA VENTE
                    
                    res = self._cr.fetchall()
                    for l in res:
                        sale_tax_id = l[0]
                        break
                    if not sale_tax_id and tax.type_tax_use == "all":
                        sale_tax_id = tax.id
                    print(sale_tax_id)
                    if sale_tax_id:
                        invoice_line_tax_ids.append(sale_tax_id)
                    else:
                        raise UserError(_("Aucune taxe équivalente n'a été trouvée!"))
                invoice_line_tax_ids = [(6,0,invoice_line_tax_ids)]
                invoice_line = (0,0,{
                                     "name":line.product_id.name,"product_id":line.product_id.id,
                                     "quantity":line.quantity,'price_unit':line.price_unit,
                                     'account_id' : line.product_id.property_account_income_id.id or line.product_id.categ_id.property_account_income_categ_id.id,
                                     'invoice_line_tax_ids':invoice_line_tax_ids
                                     })
                invoice_line_data.append(invoice_line)
                
            invoice_data["invoice_line_ids"] = invoice_line_data
            invoice = invoice_obj.create(invoice_data)
            invoice._onchange_partner_id()
            invoice._onchange_payment_term_date_invoice()
            invoices.append(invoice)
            
        if not invoices:
            raise UserError(_("Aucune facture!"))
        return True

    @api.model
    def _get_invoice_vals(self,data, partner, inv_type, journal_id,date_invoice):
        user = self.env.user
        if inv_type in ('out_invoice', 'out_refund'):
            account_id = partner.property_account_receivable_id.id
            payment_term_id = partner.property_payment_term_id.id or False
        else:
            account_id = partner.property_account_payable_id.id
            payment_term_id = partner.property_supplier_payment_term_id.id or False
        return {
            'related_invoice_id' : data.invoice_id.id,
            'vehicle_id':data.invoice_id.vehicle_id.id,
            'origin': "FR "+data.invoice_id.number,
            'date_invoice': date_invoice,
            'user_id': user.id,
            'partner_id': partner.id,
            'account_id': account_id,
            'payment_term_id': payment_term_id,
            'type': inv_type,
            'fiscal_position_id': partner.property_account_position_id.id,
            'company_id': user.company_id.id,
            'currency_id': user.company_id.currency_id.id,
            'journal_id': journal_id,
        }

