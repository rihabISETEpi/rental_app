# -*- coding: utf-8 -*-
import ast

from odoo import api, models , fields


class AgenceAgence(models.Model):
    _name = 'agence.agence'


    @api.multi
    def name_get(self):
        res = []
        for agence in self:
            name = agence.name
            if agence.code:
                name = name + ' (' + agence.code + ')'
            res.append((agence.id, name))
        return res

    code = fields.Char('Code agence', required=True)
    name = fields.Char('Nom agence', required=True)
    secteur_ids = fields.Many2many('secteur.secteur', 'secteur_agence_rel','agence_id','secteur_id', 'Secteurs')
    user_ids = fields.One2many('res.users', 'agence_id', 'Utilisateurs')

    _sql_constraints = [
        ('agence_code_uniq', 'unique(code)', "Le code de l'agence doit être unique !")
    ]

        
class SecteurSecteur(models.Model):
    _name = 'secteur.secteur'

    code = fields.Char('Code secteur', required=True)
    name = fields.Char('Nom secteur', required=True)
    agence_ids = fields.Many2many('agence.agence', 'secteur_agence_rel','secteur_id','agence_id', 'Agences')
    user_ids = fields.One2many('res.users', 'secteur_id', 'Utilisateurs')

    _sql_constraints = [
        ('agence_code_uniq', 'unique(code)', "Le code du secteur doit être unique !")
    ]

    
class ResUsers(models.Model):
    _inherit = 'res.users'

    secteur_id = fields.Many2one('secteur.secteur',"Secteur")
    agence_id = fields.Many2one('agence.agence',"Agence",domain="[('secteur_ids','=',secteur_id)]")

########## client ################################################################################
class AccountInvoiceType(models.Model):
    _name = 'account.invoice.type'
    
    code = fields.Char('Code')
    name = fields.Char('Libellé',required=True)

    @api.multi
    def name_get(self):
        result = []
        for invoice_type in self:
            name = invoice_type.name
            if invoice_type.code:
                name = name +' ( '+invoice_type.code+' )'
            result.append((invoice_type.id,name))
        return result

class ResPartnerAccount(models.Model):
    _name = 'res.partner.account'
    
    _order ="sequence asc"

    sequence = fields.Integer('Ordre')
    type_facture_id = fields.Many2one('account.invoice.type','Type facture')
    name = fields.Char('Libellé')
    mode_reglement = fields.Char('Mode rglt')
    echeance = fields.Integer('Échéance')
    account_id = fields.Many2one('account.account','Compte client',domain="[('internal_type', '=', 'receivable')]")
    supplier_account_id = fields.Many2one('account.account','Compte fournisseur',domain="[('internal_type', '=', 'payable')]")
    modifiable = fields.Boolean("Modifiable")
    partner_id = fields.Many2one('res.partner','Client')

class ResPartnerContactLine(models.Model):
    _name = 'res.partner.contact.line'
    
    type = fields.Char('Type')
    num_addr = fields.Char('Numéro / Adresse')
    name = fields.Char('Libellé')
    partner_id = fields.Many2one('res.partner','Partner')
    

class ResPartnerNationality(models.Model):
    _name = 'res.partner.nationality'
    
    name = fields.Char('Dénominarion',required=True)
    country_id = fields.Many2one('res.country','Pays')

class ResPartnerBankContract(models.Model):
    _name = "res.partner.bank.contract"

    use = fields.Boolean('Rib.')
    rib_id = fields.Many2one('res.partner.bank','RIB',readonly=True)

    sequence = fields.Integer(related='rib_id.sequence',string='Ordre',readonly=True)
    bank_name = fields.Char(related='rib_id.bank_name',string='Domicialiation',readonly=True)
    bank_code = fields.Char(related='rib_id.bank_code',string='Banque',readonly=True)
    office = fields.Char(related='rib_id.office',string='Guichet',readonly=True)
    acc_number = fields.Char(related='rib_id.acc_number',string='Compte',readonly=True)
    key = fields.Char(related='rib_id.key',string='Clé',readonly=True)
    partner_id = fields.Many2one(comodel="res.partner",related='rib_id.partner_id',string='Titulaire',readonly=True)
    contract_id = fields.Many2one('fleet.vehicle.contract','Contrat')
    
class ResPartner(models.Model):
    _inherit = 'res.partner'



    @api.multi
    @api.depends('debit','credit')
    def _get_partner_balance(self):
        for partner in self:
            partner.partner_balance = partner.debit - partner.credit

    @api.multi
    @api.depends('date_naissance')
    def _compute_age(self):
        age = 0
        for partner in self:
            if partner.date_naissance:
                diff =  fields.Date.from_string(fields.Date.context_today(self)) - fields.Date.from_string(partner.date_naissance)
                age = diff.days / 365
            partner.age = age
            

    @api.multi
    def _contract_count(self):
        contract_obj  = self.env['fleet.vehicle.contract']
        for partner in self:
            partner.contract_count = contract_obj.search_count([('partner_id','=',partner.id),('contract_cd','!=',False)])
            partner.contract_count_lld = contract_obj.search_count([('partner_id','=',partner.id),('contract_cd','=',False)])

    actif = fields.Boolean('Actif',default=True)
    title2 = fields.Many2one('res.partner.title', 'Titre')
    driver = fields.Boolean('Conducteur')
    assurance = fields.Boolean('Assurance')
    banque = fields.Boolean('Banque')
    other_account_ids = fields.One2many('res.partner.account','partner_id',string="Autres comptes")
    ##other_street_ids = fields.One2many('res.partner.street','partner_id',string="Autres adresses")
    contact_ids = fields.One2many('res.partner','parent_id',string="Autres adresses",domain=[('type','!=','contact')])
                
    contract_count = fields.Integer(compute="_contract_count", string="Nombre de contrats CD")
    contract_count_lld = fields.Integer(compute="_contract_count", string="Nombre de contrats LD")
    name2 = fields.Char('Prénom(s)')
    #ONGLET PERMIS
    #NAISSANCE
    date_naissance = fields.Date('Date de naissance')
    lieu_naissance = fields.Char('Lieu de naissance')
    nationality_id = fields.Many2one('res.partner.nationality','Nationalité')
    age = fields.Integer("Âge",compute="_compute_age")
    #PERMIS
    delivre_par = fields.Char('Délivré par')
    delivre_a = fields.Char('Délivré à')
    delivre_le = fields.Date('Délivré le')
    numero_permis = fields.Char('Numéro')
    type_permis = fields.Char('Type')
    expiration_permis = fields.Char('Expire le')
    #PASSPORT
    numero_passport = fields.Char('Numéro')
    date_delivrance = fields.Char('Date de délivrance')
    lieu_delivrance = fields.Char('À')
    expiration_passport = fields.Char('Expiration passport')
    autorite_passport = fields.Char('Autorité')
                
    partner_balance = fields.Monetary(compute="_get_partner_balance",string='Solde',store=True)
                
    #Contrat
    invoice_grouped = fields.Boolean('Factures groupées',help="Les factures sur contrat de ce parténaire vont être groupées par échéance  et moyen de paiement")
    
    ##For address
    direct = fields.Char('Direct')
    sequence = fields.Integer('Ordre')
    type = fields.Selection(
        [('contact', 'Contact'),
         ('invoice', 'Invoice address'),
         ('delivery', 'Shipping address'),
         ('local','Locale'),
         ('professional','Professionnelle'),
         ('primary','Adresse primaire'),         
         ('other', 'Other address')], string='Address Type',
        default='contact',
        help="Used to select automatically the right address according to the context in sales and purchases documents.")
    date_start = fields.Datetime("Début de validité")
    date_end = fields.Datetime("Fin de validité")
    contact_line_ids = fields.One2many('res.partner.contact.line','partner_id','Téléphone / Email')
    
    @api.onchange('active')
    def onchange_active(self):
        self.actif = self.active

    @api.onchange('actif')
    def onchange_actif(self):
        self.active = self.actif


    @api.multi
    def return_action_to_open(self):
        """ This opens the xml view specified in xml_id for the current vehicle """
        self.ensure_one()
        xml_id = self.env.context.get('xml_id')
        if xml_id:
            res = self.env['ir.actions.act_window'].for_xml_id('fleet', xml_id)
            cxt = {}
            domain = []
            partner = self
            if res.get('context'):
                cxt = ast.literal_eval(res['context'])
            if res.get('domain'):
                domain = ast.literal_eval(res.get('domain'))
            cxt.update({'default_partner_id': partner.id})
            domain.extend([('partner_id', '=', partner.id)])
            res['context'] = cxt
            res['domain'] = domain
            return res
        return False


class ResPartnerTitle(models.Model):
    _inherit = 'res.partner.title'

    company_type = fields.Selection(string='Type',
        selection=[('person', 'Individual'), ('company', 'Company')])
        

class ResCompany(models.Model):
    _inherit = 'res.company'

    min_age = fields.Integer("Âge minimum requis",default=21)
    report_logo = fields.Binary("Image rapport contrat",
                                           help="This field holds the image used as avatar for this contact, limited to 1024x1024px")
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
