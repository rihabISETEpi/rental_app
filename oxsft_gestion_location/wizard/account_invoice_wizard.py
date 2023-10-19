# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


FREQUENCY_SELECTION = [
                       ('monthly', 'Mensuelle'),
                       ('3monthly','Trimestrielle'),
                       ('6monthly','Semestrielle'),
                       ('12monthly', 'Annuelle')
                       ]

class AccountInvoiceWizard(models.TransientModel):
    _name = "account.invoice.wizard"
    
    @api.model
    def _get_journal(self):
        journal_obj = self.env['account.journal']
        journals = journal_obj.search([('type', '=', "sale")])
        return journals and journals[0].id or False
    
    @api.model
    def _get_active_id(self):
        return self.env.context.get('active_id')

    @api.model
    def _get_type_facture_id(self):
        model,type_id = self.env['ir.model.data'].get_object_reference('account','account_invoice_type_OR')
        return type_id

    
    type_facture_id = fields.Many2one('account.invoice.type',"Type de facture",default=_get_type_facture_id)
    mro_id = fields.Many2one('mro.order','OR',default=_get_active_id,required=True,ondelete="cascade")

    journal_id = fields.Many2one('account.journal', 'Destination Journal',default=_get_journal)


    @api.multi
    def create_invoice(self):
        invoice_exists = False
        invoice_obj = self.env['account.invoice']
        invoice_line_obj = self.env['account.invoice.line']
        invoices = []
        ai_data = {}
        ai_line_data =  {}
        for data in self:
            for line in data.mro_id.parts_lines:
                prev_invoice_line_id = invoice_line_obj.search([('mro_line_id','=',line.id)])
                if prev_invoice_line_id: ###SI LA LIGNE A DÉJÀ ÉTÉ FACTURÉE
                    invoice_exists = True
                    continue
                if line.to_invoice and line.partner_id.id:
                    ai_data.setdefault(line.partner_id.id, [])
                    ai_line_data.setdefault(line.partner_id.id, [])
                    ai_data[line.partner_id.id] =  self._get_invoice_vals(data, line.partner_id, "out_invoice", data.journal_id.id)
                    account_id = line.parts_id.property_account_income_id.id or line.parts_id.categ_id.property_account_income_categ_id.id or data.journal_id.default_credit_account_id.id
                    ai_line = (0,0,{"mro_line_id":line.id,"name":line.parts_id.name,"product_id":line.parts_id.id,"account_id":account_id,"quantity":line.parts_qty,'price_unit':line.price_unit2})
                    ai_line_data[line.partner_id.id].append(ai_line)
                    
            for key,invoice_data in ai_data.items():
                invoice_data["invoice_line_ids"] = ai_line_data[key]
                invoice = invoice_obj.create(invoice_data)
                invoices.append(invoice)
        if not invoices:
            if invoice_exists:
                raise UserError(_("Facture(s) déjà créée(s)!"))
            raise UserError(_("Aucune facture!"))
        return True


    def _get_invoice_vals(self,data, partner, inv_type, journal_id):
        user = self.env.user

        if inv_type in ('out_invoice', 'out_refund'):
            account_id = partner.property_account_receivable_id.id
            payment_term_id = partner.property_payment_term_id.id
        else:
            account_id = partner.property_account_payable_id.id
            payment_term_id = partner.property_supplier_payment_term_id.id
        return {
            "mro_id":data.mro_id.id,
            "type_facture_id":data.type_facture_id.id,
            'vehicle_id':data.mro_id.vehicle_id.id,
            'origin': data.mro_id.name,
            'date_invoice': data.mro_id.date_start,
            'user_id': self.env.user.id,
            'partner_id': partner.id,
            'account_id': account_id,
            'payment_term_id': payment_term_id,
            'type': inv_type,
            'fiscal_position_id': partner.property_account_position_id.id,
            'company_id': user.company_id.id,
            'currency_id': user.company_id.currency_id.id,
            'journal_id': journal_id,
        }

class AccountInvoicePreviewWizard(models.Model):
    _name = "account.invoice.preview.wizard"
    _inherit = "account.invoice"

    @api.onchange('invoice_line_ids')
    def _onchange_invoice_line_ids(self):
        return

    @api.one
    @api.depends('contract_id')
    def _compute_amount(self):
        if 'driver_invoice' in self.env.context:
            self.amount_untaxed  = self.contract_id.driver_amount_untaxed
            self.amount_tax  = self.contract_id.driver_aamount_tax
            self.amount_total  = self.contract_id.driver_aamount_total
        else:
            self.amount_untaxed  = self.contract_id.amount_untaxed
            self.amount_tax  = self.contract_id.amount_tax
            self.amount_total  = self.contract_id.amount_total
    
    @api.multi
    def create_invoice(self):
        return True

    @api.model
    def create(self,vals):
        w = super(AccountInvoicePreviewWizard,self).create(vals)
        self.env['account.invoice'].create(vals)
        return w

    @api.model
    def default_get(self, fields_list):
        res = super(AccountInvoicePreviewWizard,self).default_get(fields_list)
        contract = self.env['fleet.vehicle.contract'].browse(self.env.context.get('active_id'))
        model,type_id = self.env['ir.model.data'].get_object_reference('account','account_invoice_type_CD')
        res.update(type_facture_id=type_id)
        res.update(agence_id=contract.src_agence_id.id)
        invoice_line_ids = []
        if 'driver_invoice' in self.env.context:
            res.update(partner_id=contract.driver_id.id)
            for line in contract.driver_prestation_ids:
                price_unit = line.price_untaxed
                invoice_line_ids.append((0,0,{
                                     'product_id': line.product_id.id,
                                     'name' : line.name,
                                     'account_id' : line.account_id.id,
                                     'quantity': line.product_qty,
                                     'price_unit': price_unit,
                                     'invoice_line_tax_ids' : line.invoice_line_tax_ids.ids,
                                     'discount' : line.discount,
                                     }))
        else:
            res.update(partner_id=contract.partner_id.id)
            for line in contract.prestation_ids:
                price_unit = line.price_untaxed
                print(line.price_untaxed)
                invoice_line_ids.append((0,0,{
                                     'product_id': line.product_id.id,
                                     'name' : line.name,
                                     'account_id' : line.account_id.id,
                                     'quantity': line.product_qty,
                                     'price_unit': price_unit,
                                     'invoice_line_tax_ids' : line.invoice_line_tax_ids.ids,
                                     'discount' : line.discount,
                                     }))
        res.update(
                    invoice_line_ids=invoice_line_ids
                    )
        return res

class account_invoice_contract_wizard(models.Model):
    _name = "account.invoice.contract.wizard"
    
    @api.model
    def _get_company_id(self):
        return self.env.user.company_id.id
    
    company_id = fields.Many2one("res.company","Société",default=_get_company_id)
    type_id = fields.Many2one('fleet.vehicle.contract.type','Type',domain=[('contract_cd','=',False)])
    contract_id  = fields.Many2one('fleet.vehicle.contract','Contrat',domain=[('state','=','open'),('contract_cd','=',False)])
    partner_id = fields.Many2one('res.partner','Client')
    date_invoice = fields.Date('Date de facturation',required=True)
    date_end = fields.Date("Simuler une date d'arrêt")
    period_id = fields.Many2one('fleet.vehicle.contract.period','Période à selectionner',required=True)
    agence_id = fields.Many2one('agence.agence','Agence de départ')
    frequency = fields.Selection(FREQUENCY_SELECTION,"Périodicité")
    echeance = fields.Boolean('Terme échu')
    validate_invoices = fields.Boolean('Comptabiliser les factures générées',help="Si cette option est cochée , les factures générées seront automatiquement comptabilisées.")

    @api.onchange('date_invoice')
    def onchange_date_invoice(self):
        period = self.env['fleet.vehicle.contract.period'].find(self.date_invoice)
        self.period_id = period[0].id
    
    
    @api.multi
    def action_validate(self):
        contract_obj  = self.env['fleet.vehicle.contract']
        domain = [('state','=','open'),('contract_cd','=',False),('echeance','=',self.echeance)]
        if self.company_id:
            domain.append(('company_id','=',self.company_id.id))
        if self.agence_id:
            domain.append(('agence_id','=',self.agence_id.id))
        if self.type_id:
            domain.append(('type_id','=',self.type_id.id))
        if self.frequency:
            domain.append(('frequency','=',self.frequency))
        if self.contract_id:
            domain.append(('id','=',self.contract_id.id))
        if self.partner_id:
            domain.append(('partner_id','=',self.partner_id.id))
        contracts = contract_obj.search(domain)
        contracts._recurring_create_invoice(date_invoice=self.date_invoice,wizard_period_id=self.period_id.id,validate_invoices=self.validate_invoices)
        return True

