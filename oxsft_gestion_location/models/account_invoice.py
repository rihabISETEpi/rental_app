# -*- coding: utf-8 -*-
from datetime import date

from odoo import models, fields, api,_
from odoo.exceptions import UserError


class AccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'

   
    mro_line_id = fields.Many2one('mro.order.parts.line', 'Ligne mro')
    contract_id = fields.Many2one('fleet.vehicle.contract','Contrat',domain=[('state','=','open')])
    contract_cd = fields.Boolean('Contrat CD')
    vehicle_id = fields.Many2one("fleet.vehicle",string='Véhicule',readonly=True)
    agence_id = fields.Many2one("agence.agence",string='Agence',readonly=True)
    contract_date_start = fields.Date('Date début de facture')
    contract_date_end = fields.Date('Date fin de facture')

    @api.model
    def create(self, vals):
        invoice_line = super(AccountInvoiceLine, self).create(vals)
        invoice = invoice_line.invoice_id
        line_obj = self.env['fleet.vehicle.operation.report']
        domain = [('parts_line_id', '=', invoice_line.mro_line_id.id),
                  ('purchase_line_id', '=', False),
                  ('invoice_line_id', '=', False)]
        line_obj.search(domain).unlink()
        data_invoice = {
                         'nature' : 'fr',
                         'type' : 'invoice',
                         's_type' : 'standard',
                         'statut' : 'invoice',
                         'libelle_operation' : invoice_line.name,
                         'mro_id' : invoice.mro_id.id,
                         'date' : invoice.mro_id.date_start,
                         'odometer' : invoice.mro_id.km_start or invoice.vehicle_id.odometer,
                         'partner_id' : invoice.partner_id.id,
                         
                         'invoice_id' : invoice.id,
                         
                         'vehicle_id' : invoice.vehicle_id.id,
                         'purchase_line_id' :invoice_line.purchase_line_id.id,
                         'invoice_line_id' :invoice_line.id
                    }
        if invoice.type in ('out_invoice', 'out_refund'):
            data_invoice['nature'] = 'clt'
            clt_quantity = invoice_line.quantity
            clt_ht = invoice_line.quantity * invoice_line.price_unit
            data_invoice['clt_quantity'] = clt_quantity
            data_invoice['clt_ht'] = clt_ht
            if invoice_line.product_id.historique:  # #il faut que l'article soit prévu pour être ajouté dans l'historique
                line_obj.create(data_invoice)
        else:
            fr_quantity = invoice_line.quantity
            fr_ht = invoice_line.quantity * invoice_line.price_unit
            data_invoice['fr_quantity'] = fr_quantity
            data_invoice['fr_ht'] = fr_ht
            line_id = line_obj.search([('purchase_line_id', '=', invoice_line.purchase_line_id.id), ('purchase_line_id', '!=', False)])
            if line_id:
                line_id.write(data_invoice)  # #SI LA COMMANDE FOURNISSEUR AVAIT DEJA CREE UNE LIGNE
            else:
                if invoice_line.product_id.historique:  # ##SI LA FACTURE OU L'AVOIR ACHAT A ÉTÉ CRÉÉ DIRECTEMENT
                    line_obj.create(data_invoice)
        
        ###MRO LINE
        if invoice_line.purchase_line_id:
            invoice_line.write({'mro_line_id':invoice_line.purchase_line_id.mro_line_id.id})
        
        ###MAT
        if invoice_line.sale_line_ids:
            vehicle = invoice_line.sale_line_ids[0].order_id.vehicle_id
            invoice_line.write({'vehicle_id':vehicle.id})
            if not invoice_line.invoice_id.vehicle_id:
                invoice_line.invoice_id.write({'vehicle_id':vehicle.id})
        return invoice_line

    @api.multi
    def write(self, vals):
        result = super(AccountInvoiceLine, self).write(vals)
        line_obj = self.env['fleet.vehicle.operation.report']
        for invoice_line in self: 
            invoice = invoice_line.invoice_id
            line_id = line_obj.search([('invoice_line_id', '=', invoice_line.id), ('invoice_line_id', '!=', False)])
            data_invoice = {
                         'type' : 'invoice',
                         's_type' : 'standard',
                         'statut' : 'invoice',
                         'libelle_operation' : invoice_line.name,
                         'mro_id' : invoice.mro_id.id,
                         'date' : invoice.mro_id.date_start,
                         'odometer' : invoice.mro_id.km_start or invoice.vehicle_id.odometer,
                         'partner_id' : invoice.partner_id.id,
                         'invoice_id' : invoice.id,
                         # 'date_facture' : invoice.date_invoice,
                         'vehicle_id' : invoice.vehicle_id.id,
                         'purchase_line_id' :invoice_line.purchase_line_id.id,
                         'invoice_line_id' :invoice_line.id
                    }
            if invoice.type in ('out_invoice', 'out_refund'):
                data_invoice['nature'] = 'clt'
                clt_quantity = invoice_line.quantity
                clt_ht = invoice_line.quantity * invoice_line.price_unit
                data_invoice['clt_quantity'] = clt_quantity
                data_invoice['clt_ht'] = clt_ht
            else:
                data_invoice['nature'] = 'fr'
                fr_quantity = invoice_line.quantity
                fr_ht = invoice_line.quantity * invoice_line.price_unit
                data_invoice['fr_quantity'] = fr_quantity
                data_invoice['fr_ht'] = fr_ht
            line_id.write(data_invoice)
        
        return result

class AccountInvoice(models.Model):
    _inherit = 'account.invoice'
    _order = "contract_date_start asc,number desc, id desc"

    @api.model
    def _prepare_refund(self, invoice, date_invoice=None, date=None, description=None, journal_id=None):
        """ Prepare the dict of values to create the new refund from the invoice.
            This method may be overridden to implement custom
            refund generation (making sure to call super() to establish
            a clean extension chain).

            :param record invoice: invoice to refund
            :param string date_invoice: refund creation date from the wizard
            :param integer date: force date from the wizard
            :param string description: description of the refund from the wizard
            :param integer journal_id: account.journal from the wizard
            :return: dict of value to create() the refund
        """
        values = super(AccountInvoice, self)._prepare_refund(invoice, date_invoice, date, description, journal_id)
        values['vehicle_id'] = invoice.vehicle_id.id
        values['mro_id'] = invoice.mro_id.id
        return values
    
    @api.model
    def _get_agence_id(self):
        return self.env.user.agence_id

    @api.one
    @api.depends("vehicle_id")
    def _compute_vehicle_data(self):
        self.c_vehicle_id = self.vehicle_id.id
        self.c_license_plate = self.vehicle_id.license_plate
        self.c_odometer = int(self.vehicle_id.odometer)
        self.c_libelle = self.vehicle_id.libelle
        
   
    vehicle_id = fields.Many2one('fleet.vehicle', 'Matériel', readonly=True, states={'draft': [('readonly', False)]})
    mro_id = fields.Many2one('mro.order', 'OR', readonly=True, states={'draft': [('readonly', False)]})
    type_achat = fields.Selection([('achat', 'Achat'), ('carburant', 'Carburant'), ('vehicule', 'Véhicule'), ('remorque', 'Remorque'), ('entretien', 'Entretien'), ('assistance', 'Assistance')], 'Type achat', readonly=True, states={'draft': [('readonly', False)]})
    type_facture_id = fields.Many2one('account.invoice.type', "Type de facture", readonly=True, states={'draft': [('readonly', False)]})
    date_invoice = fields.Date(string='Invoice Date',
                                     readonly=True, states={'draft': [('readonly', False)]}, index=True,
                                     help="Keep empty to use the current date", copy=False,default=fields.Date.context_today)
    date_invoice2 = fields.Date('Date de facture', readonly=True, states={'draft': [('readonly', False)]},default=fields.Date.context_today)
    contract_date_start = fields.Date('Date début de facture',readonly=True)
    contract_date_end = fields.Date('Date fin de facture',readonly=True)
        
    delivery_address_id = fields.Many2one('res.partner','Adresse de livraison',domain="[('parent_id','=',partner_id),('type','=','delivery')]")
        
    c_vehicle_id = fields.Char(string='ID :',compute="_compute_vehicle_data",store=True)
    c_license_plate = fields.Char(string='Immatriculation :', compute="_compute_vehicle_data",store=True)
    c_odometer = fields.Char(string='Compteur :', compute="_compute_vehicle_data",store=True)
    c_libelle = fields.Char(string='Libellé :', compute="_compute_vehicle_data",store=True)
    agence_id = fields.Many2one('agence.agence', "Agence",default=_get_agence_id)
        
    contract_id = fields.Many2one('fleet.vehicle.contract', 'Contrat')
    
    contract_period_id = fields.Many2one("fleet.vehicle.contract.period",u"Période")
    
    

    state = fields.Selection([
            ('draft','Draft'),
            ('proforma', 'Pro-forma'),
            ('proforma2', 'Pro-forma'),
            ('open', 'Comptabilisé'),
            ('paid', 'Paid'),
            ('cancel', 'Cancelled'),
        ], string='Status', index=True, readonly=True, default='draft',
        track_visibility='onchange', copy=False,
        help=" * The 'Draft' status is used when a user is encoding a new and unconfirmed Invoice.\n"
             " * The 'Pro-forma' status is used when the invoice does not have an invoice number.\n"
             " * The 'Open' status is used when user creates invoice, an invoice number is generated. It stays in the open status till the user pays the invoice.\n"
             " * The 'Paid' status is set automatically when the invoice is paid. Its related journal entries may or may not be reconciled.\n"
             " * The 'Cancelled' status is used when user cancel invoice.")



    @api.multi
    def unlink(self):
        ''' 
            Changer la méthode de suppression pour tenir compte de la saisie manuelle du numéro de facture pour le fournisseur
        '''
        for invoice in self:
            if invoice.state not in ('draft', 'cancel'):
                raise UserError(_('You cannot delete an invoice which is not draft or cancelled. You should refund it instead.'))
            elif invoice.move_name and invoice.type !='in_invoice':
                raise UserError(_('You cannot delete an invoice after it has been validated (and received a number). You can set it back to "Draft" state and modify its content, then re-confirm it.'))
        return models.Model.unlink(self)

    @api.model
    def create(self, vals):
        if not vals.get('vehicle_id'):
            if self.env.context.get('active_model') == 'stock.picking':
                pick = self.env["stock.picking"].browse(self.env.context.get('active_id'))
                vals['vehicle_id'] = pick.vehicle_id.id
                if not vals.get('mro_id'):
                    vals['mro_id'] = pick.mro_id.id

        
        if 'number' in vals:
            vals['move_name'] = vals['number']  ### Prob : le client veut saisir manuellement le numéro de facture
        invoice = super(AccountInvoice, self).create(vals)
        if 'move_name' in vals:
            invoice.write({"number":vals['move_name']})
        return invoice

    @api.multi
    def write(self, vals):
        return super(AccountInvoice, self).write(vals)


    @api.multi
    def action_move_create(self):
        for invoice in self:
            if invoice.type == "in_invoice":
                same_number_ids = self.search([('number', '=', invoice.number), ('id', '!=', invoice.id)])
                if same_number_ids:
                    raise UserError(_('Vous ne pouvez pas saisir deux numéros de factures pour le même fournisseur.Veuillez changer votre saisie!'))
        return super(AccountInvoice, self).action_move_create()
    
    @api.onchange('type_facture_id')
    def onchange_type_facture_id(self):
        if self.partner_id:
            account_id = False
            p = self.partner_id
            rec_account = p.property_account_receivable_id
            pay_account = p.property_account_payable_id
            
            if type in ('out_invoice', 'out_refund'):
                account_id = rec_account.id
            else:
                account_id = pay_account.id
                
            type_facture = self.env['res.partner.account'].search([('type_facture_id', '=', self.type_facture_id.id), ('partner_id', '=', p.id)], order="sequence asc")
            if type_facture:
                if type in ('out_invoice', 'out_refund'):
                    account_id = type_facture[0].account_id.id
                else:
                    account_id = type_facture[0].supplier_account_id.id
            self.account_id = account_id
                
    @api.onchange('partner_id', 'company_id')
    def _onchange_partner_id(self):
        payment_mode_id = False
        res = super(AccountInvoice,self)._onchange_partner_id()
        self.onchange_type_facture_id()
        partner = self.partner_id
        if type in ('out_invoice', 'out_refund'):
            payment_mode_id = partner.customer_payment_mode_id.id
        else:
            payment_mode_id = partner.supplier_payment_mode_id.id
        
        self.payment_mode_id = payment_mode_id 
        return res

    @api.onchange('payment_term_id', 'date_invoice','date_invoice2')
    def _onchange_payment_term_date_invoice(self):
        if self.type in ('out_invoice', 'out_refund'):
            date_invoice = self.date_invoice
        else:
            date_invoice = self.date_invoice2
            
        if not date_invoice:
            date_invoice = fields.Date.context_today(self)
        if not self.payment_term_id:
            # When no payment term defined
            self.date_due = self.date_due or date_invoice
        else:
            pterm = self.payment_term_id
            pterm_list = pterm.with_context(currency_id=self.currency_id.id).compute(value=1, date_ref=date_invoice)[0]
            self.date_due = max(line[0] for line in pterm_list)


    @api.onchange('purchase_id')
    def purchase_order_change(self):
        if self.purchase_id.vehicle_id:
            self.vehicle_id= self.purchase_id.vehicle_id.id
        self.mro_id= self.purchase_id.mro_id.id
        if self.purchase_id.type_facture_id:
            self.type_facture_id= self.purchase_id.type_facture_id.id
        if self.purchase_id.agence_id:
            self.agence_id= self.purchase_id.agence_id.id
        return super(AccountInvoice,self).purchase_order_change()


    