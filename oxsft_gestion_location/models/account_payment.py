# -*- coding: utf-8 -*-

from odoo import models, fields, api


class account_payment(models.Model):
    _inherit = "account.payment"

    partner_bank_id = fields.Many2one('res.partner.bank', string='RIB',
                                                    help='Bank Account Number to which the invoice will be paid. A Company bank account if this is a Customer Invoice or Supplier Refund, otherwise a Partner bank account number.',
                                                    readonly=True, states={'draft': [('readonly', False)]})
    date_due = fields.Date(string="Date d'échéance",
                                            readonly=True, states={'draft': [('readonly', False)]})
                
    payment_mode_id = fields.Many2one('account.payment.mode', 'Mode de règlement')
        


    @api.model
    def default_get(self, fields):
        rec = super(account_payment, self).default_get(fields)
        invoice_defaults = self.resolve_2many_commands('invoice_ids', rec.get('invoice_ids'))
        if invoice_defaults and len(invoice_defaults) == 1:
            invoice = invoice_defaults[0]
            if invoice.get('partner_bank_id'):
                rec['partner_bank_id'] = invoice['partner_bank_id'][0]
            rec['date_due'] = invoice['date_due']
            if invoice.get('payment_mode_id'):
                rec['payment_mode_id'] = invoice['payment_mode_id'][0]
        return rec

