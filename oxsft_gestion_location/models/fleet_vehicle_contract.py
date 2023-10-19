# -*- coding: utf-8 -*-
import calendar
from datetime import timedelta
from dateutil import relativedelta
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError


_logger = logging.getLogger(__name__)

FREQUENCY_SELECTION = [
                       ('monthly', 'Mensuelle'),
                       ('3monthly','Trimestrielle'),
                       ('6monthly','Semestrielle'),
                       ('12monthly', 'Annuelle')
                       ]

FREQUENCY_TYPE_SELECTION = [
                            ('30', '30 jours'),
                            ('real','Réel'),
                            ('no_prorata','Sans prorata')
                            ]          

CONTRACT_STATE = [('waiting','En attente'),
                  ('devis', 'Devis'),
                  ('reservation', 'Réservation'),
                  ('open', 'Contrat'),
                  ('depart','Départ'), 
                  ('closed', 'Clos')]              


class FleetVehicleContract(models.Model):

    _name = 'fleet.vehicle.contract'
    _order = 'state desc,expiration_date'


    @api.one
    @api.returns('ir.ui.view')
    def get_formview_id(self):
        if self.contract_cd:
            return self.env.ref('fleet.fleet_vehicle_contract_form')
        else:
            return self.env.ref('fleet.fleet_vehicle_contract_lld_form')
    
    @api.model
    def _get_default_contract_type_id(self):
        contract_cd = self.env.context.get('default_contract_cd')
        type_id = self.env['fleet.vehicle.contract.type'].search([('contract_cd', '=', contract_cd)])
        return type_id and type_id[0].id or False

    @api.model
    def _get_company_id(self):
        return self.env.user.company_id.id
    
    @api.model
    def _get_src_agence_id(self):
        return self.env.user.agence_id.id
    
    @api.model
    def _get_dest_agence_id(self):
        return self.env.user.agence_id.id

    @api.model
    def _get_ret_src_agence_id(self):
        return self.env.user.agence_id.id
    
    @api.model
    def _get_ret_dest_agence_id(self):
        return self.env.user.agence_id.id

    @api.one
    def _get_company_currency(self):
        if self.company_id:
            self.currency_id = self.sudo().company_id.currency_id
        else:
            self.currency_id = self.env.user.company_id.currency_id

    @api.one
    @api.depends('prestation_ids','prestation_ids.amount_untaxed','prestation_ids.amount_tax','prestation_ids.amount_total', 'currency_id')
    def _amount_all(self):
        amount_untaxed = amount_tax = amount_total = 0.0
        for line in self.prestation_ids:
            amount_untaxed += line.amount_untaxed
            amount_tax += line.amount_tax
            amount_total += line.amount_total
        self.amount_untaxed = amount_untaxed
        self.amount_tax = amount_tax
        self.amount_total = amount_total

    @api.one
    @api.depends('driver_prestation_ids','driver_prestation_ids.amount_untaxed','driver_prestation_ids.amount_tax','driver_prestation_ids.amount_total', 'currency_id')
    def _driver_amount_all(self):
        driver_amount_untaxed = driver_amount_tax = driver_amount_total = 0.0
        for line in self.driver_prestation_ids:
            driver_amount_untaxed += line.amount_untaxed
            driver_amount_tax += line.amount_tax
            driver_amount_total += line.amount_total
        self.driver_amount_untaxed = driver_amount_untaxed
        self.driver_amount_tax = driver_amount_tax
        self.driver_amount_total = driver_amount_total


    @api.one
    @api.depends("ret_end_odometer","ret_vehicle_odometer")
    def _get_odometer_variation(self):
        self.ret_diff_odometer = self.ret_end_odometer - self.ret_vehicle_odometer


    @api.multi
    def _count_all(self):
        invoice_obj = self.env['account.invoice']
        invoice_line_obj = self.env['account.invoice.line']
        move_obj = self.env['fleet.vehicle.move']
        r_obj = self.env["fleet.vehicle.contract.stop"]
        
        for contract in self:
            invs = invoice_obj.search([('contract_id','=',contract.id),('type', 'in', ('out_invoice', 'out_refund'))])
            inv_lines=invoice_line_obj.search([('contract_id','=',contract.id),('invoice_id.type', 'in', ('out_invoice', 'out_refund'))])
            inv_ids = invs.ids
            for inv_line in inv_lines:
                inv_ids.append(inv_line.invoice_id.id)
            inv_ids = set(inv_ids)
            contract.contract_count = len(inv_ids)
            contract.bail_count = len(contract.bail_ids)
            contract.move_count = move_obj.search_count([('contract_id','=',contract.id)])
            contract.fiche_r_count = r_obj.search_count([('contract_id','=',contract.id)])
   
    @api.one
    @api.depends("num_contract","num_resa","num_devis")
    def _get_contract_name(self):
        name = "AUCUN ID"
        if self.num_contract:
            name = self.num_contract
        elif self.num_resa:
            if self.contract_cd:
                name = self.num_resa
        elif self.num_devis:
            if self.contract_cd:
                name = self.num_devis
        self.name = name

    @api.one
    @api.depends("vehicle_odometer")
    def _compute_ret_vehicle_odometer(self):
        self.ret_vehicle_odometer = self.vehicle_odometer
        
    @api.one
    @api.depends("category_id")
    def _get_category_name(self):
        self.category_name = self.category_id.name
        
    @api.one
    @api.depends("src_agence_id")
    def _get_src_agence_name(self):
        self.src_agence_name = self.src_agence_id.name

    @api.one
    @api.depends("start_date","expiration_date")
    def _compute_nombre_jour(self):
        nombre_jour = 0
        try:
            diff = fields.Date.from_string(self.expiration_date) - fields.Date.from_string(self.start_date)
            nombre_jour = diff.days
        except:
            pass
        self.nombre_jour = nombre_jour

    @api.one
    @api.depends("start_date","expiration_date")
    def _compute_lld_nombre_mois(self):
        lld_nombre_mois = 0
        try:
            diff = fields.Date.from_string(self.expiration_date) - fields.Date.from_string(self.start_date)
            lld_nombre_mois = diff.days/30
        except:
            pass
        self.lld_nombre_mois = lld_nombre_mois

        
        
    name  = fields.Char(compute="_get_contract_name",string='Référence',store=True)
    num_contract = fields.Char('N° contrat :')
    num_resa = fields.Char('Résa :')
    num_devis = fields.Char('Devis :')
    avenant = fields.Integer('Avenant :',readonly=True)
    voucher = fields.Char("N° de voucher")
    contract_date_stop = fields.Date("Date de fin du contrat",readonly=True)
    avenant_date_start = fields.Date("Date de début de l'avenant",readonly=True)
    contract_id = fields.Many2one('fleet.vehicle.contract','Contrat lié',domain=[('contract_cd','=',False)],readonly=True)
    contract_count = fields.Integer(compute="_count_all", string="Nombre de factures")
    bail_count =fields.Integer(compute="_count_all", string="Nombre de cautions")
    move_count = fields.Integer(compute="_count_all", string="Nombre de mouvements")
    fiche_r_count = fields.Integer(compute="_count_all", string="Restitions")
    date = fields.Date('Date :',default=fields.Date.today())
    start_date = fields.Datetime('Départ le :', help='Date de début du contrat',default=fields.Datetime.now)
    expiration_date = fields.Datetime('Retour prévu le :', help="Date d'expiration du contrat)")
        
        
    state = fields.Selection(CONTRACT_STATE,
                                  'Statut', readonly=True,
                                  copy=False,default="devis")
    
    category_id = fields.Many2one('fleet.vehicle.category', 'Catégorie :')
    category_name = fields.Char(compute="_get_category_name",string="Libellé catégorie",store=True) ## only for planning purpuse
    nombre_jour = fields.Integer('Jrs prévus :',compute="_compute_nombre_jour",store=True,readonly=False)
    planned_odometer = fields.Float('Km prévus :')

    src_agence_id = fields.Many2one('agence.agence', 'Départ :',default=_get_src_agence_id)
    src_agence_name = fields.Char(compute="_get_src_agence_name",string="Libellé agence déoart",store=True) ## only for planning purpuse
    dest_agence_id = fields.Many2one('agence.agence', 'Agence Ret. Prév. :',default=_get_dest_agence_id)
    partner_id = fields.Many2one('res.partner', 'Client :', required=True)
    currency_id = fields.Many2one('res.currency', compute='_get_company_currency', readonly=True,
        string="Currency", help='Utility field to express amount currency')
    partner_balance = fields.Monetary(related='partner_id.partner_balance', string='Solde client :', readonly=True)
    partner_name = fields.Char(related='partner_id.name', string='Client :', readonly=True)
    driver_id = fields.Many2one('res.partner', 'Conducteur :', domain="[('driver','=',True)]")
    driver_ids = fields.Many2many('res.partner', 'vehicle_contract_driver_rel', 'contract_id', 'driver_id', string='Conducteurs :', domain="[('driver','=',True)]")
    vehicle_id = fields.Many2one('fleet.vehicle', 'Parc :')
    vehicle_license_plate = fields.Char(related='vehicle_id.license_plate',string='Immatriculation :')
    vehicle_category_id = fields.Many2one("fleet.vehicle.category",related='vehicle_id.category_id',string="Cat. :")
    vehicle_odometer = fields.Float(string='Km départ :')
        
    type_id = fields.Many2one('fleet.vehicle.contract.type', 'Type :',required=True,default=_get_default_contract_type_id)
    #type_code = fields.Char(related='type_id.code',string='Code du type de contrat')
    contract_cd = fields.Boolean('Contrat courte durée')
        
    notes = fields.Text('Notes')
        
    amount = fields.Float('Montant')
        
    contact_ids = fields.One2many('fleet.vehicle.contract.contact', 'contract_id', 'Contacts')
        
    payment_mode_id = fields.Many2one('account.payment.mode', 'Moyen de rglt :')
    property_payment_term_id = fields.Many2one('account.payment.term', 'Échéance :')
    driver_collectif = fields.Char('Collectif :')
    driver_regroupement = fields.Char('Code de Regroupt Fact :')
    user_id = fields.Many2one('res.users', 'Commercial')
    ref = fields.Char('Réf client :')
    purchaser_id = fields.Many2one('res.partner', 'Fournisseur :')
    purchase_price = fields.Float('Prix achat matériel :')
        
    km_sup_price_unit = fields.Float('Px CptSup')
    frequency = fields.Selection(FREQUENCY_SELECTION, 'Périodicité :',default="monthly")
    frequency_type = fields.Selection(FREQUENCY_TYPE_SELECTION, 'Mensualité :',default="30")
    agence_id2 = fields.Many2one('agence.agence', 'Agence / Soc :')

        
    lld_nombre_mois = fields.Integer('Durée :',compute="_compute_lld_nombre_mois",store=True,readonly=True)
        
    vehicle_libelle = fields.Char('Libellé commerciale :')
    vehicle_position_id = fields.Many2one('fleet.vehicle.move','Position manuelle :')
    
    recurring_last_date = fields.Date('Dernière date Fac :')
    period_id = fields.Many2one('fleet.vehicle.contract.period', 'Prochaine Fac en :')
    date_envoi = fields.Date("Envoi contrat :")
    date_signature = fields.Date("Retour signature :")
    agence_id = fields.Many2one('agence.agence', 'Agence :')
    company_id = fields.Many2one('res.company', 'Code Société :',required=True,default=_get_company_id)
    echeance = fields.Boolean('Terme échu')
        
    prestation_ids = fields.One2many('fleet.vehicle.contract.prestation', 'contract_id', 'Prestations')
        
    amount_untaxed = fields.Monetary(compute="_amount_all", string='Montant HT',store=True)
    amount_tax = fields.Monetary(compute="_amount_all", string='Montant TVA',store=True)
    amount_total = fields.Monetary(compute="_amount_all", string='Montant TTC',store=True)

    ##Driver
    driver_invoice_ok = fields.Boolean('Prise en charge')
    driver_prestation_ids = fields.One2many('fleet.vehicle.contract.prestation', 'driver_contract_id', 'Prestations conducteur')
        
    driver_amount_untaxed = fields.Float(compute="_driver_amount_all", string='Montant HT',store=True)
    driver_amount_tax = fields.Float(compute="_driver_amount_all", string='Montant TVA',store=True)
    driver_amount_total = fields.Float(compute="_driver_amount_all", string='Montant TTC',store=True)


    base = fields.Float('Base locative')
    valeur_residuelle = fields.Float("Valeur résiduelle :")
    frais_dossier = fields.Float("Frais de dossier :")
    rate_fi = fields.Float("Taux Fi annuel % :")
    montant_loyer = fields.Float("Mt loyer Fi :")
        
    fuel_description = fields.Char('Decriptions')
    fuel = fields.Integer('Carburant')
    ret_fuel1 = fields.Integer('Carburant')
    ret_fuel2 = fields.Integer('Carburant')
    ret_vehicle_odometer = fields.Float('Cpt départ :',compute="_compute_ret_vehicle_odometer")
    ret_end_odometer = fields.Float('Cpt retour :')
    ret_diff_odometer = fields.Float(compute="_get_odometer_variation", string='Parcourus :')
    ret_invoice_fuel1 = fields.Float('Quantité à facturer(Litre) :')
    ret_invoice_fuel2 = fields.Float('Qté carb. 2 à facturer(Litre) :')
    ret_date = fields.Datetime('Retour le :')
    ret_src_agence_id = fields.Many2one('agence.agence', 'Départ :',default=_get_ret_src_agence_id)
    ret_dest_agence_id = fields.Many2one('agence.agence', 'Retour :',default=_get_ret_dest_agence_id)
        
    pricelist_id = fields.Many2one('product.pricelist', 'Tarif')
    item_id = fields.Many2one('product.pricelist.item', 'Méthode',domain="[('pricelist_id','=',pricelist_id)]")
        
    total_odometer = fields.Float('Cumul cpt :')
    total_fuel_qty = fields.Float('Cumul carburant :')
    total_odometer_relay = fields.Float('Cumulé cpt en relais :')
    # RETOUR LLD
    lld_ret_move_done = fields.Datetime('Terminé le :')
    lld_ret_ecart_jour = fields.Integer('Écart jour :')
    lld_ret_new_end = fields.Datetime('Fin prolongée :')
    ret_ecart_km = fields.Float(string=u'Écart :',compute="_compute_ret_ecart_km")
        
    return_ok = fields.Boolean('Le retour a été validé')
    booking = fields.Boolean('Surbooking :')
    display_all = fields.Boolean('Tout le parc',default=True)
        
    # Onglet Client contrat LLDklt
    partner_ref = fields.Char(related='partner_id.ref',string='Code :',readonly=True)
    partner_name = fields.Char(related='partner_id.name',string='Nom :',readonly=True)
    partner_street = fields.Char(related='partner_id.street',string='Adresse :',readonly=True)
    partner_street2 = fields.Char(related='partner_id.street2',string='Adresse2 :',readonly=True)
    partner_zip = fields.Char(related='partner_id.zip',string='Code postal :',readonly=True)
    partner_city_id = fields.Many2one("res.city",related='partner_id.city_id',string='Ville :',readonly=True)
    partner_country_id = fields.Many2one("res.country",related='partner_id.country_id',string='Pays :',readonly=True)
    partner_contact_ids = fields.One2many('fleet.vehicle.contract.contact', 'lld_contract_id',string='Contacts longue durée :')
    
    
    km_frequency = fields.Selection(FREQUENCY_SELECTION, "Périodicité(Km)")
    km_ecart = fields.Float("Tolérance")
    auto_ok = fields.Boolean("Dans consommation ( km )")
        
    contract_vehicle_ids = fields.One2many('contract.vehicle.odometer','contract_id','Changement')
    bail_ids = fields.One2many('fleet.vehicle.contract.bail','contract_id','Cautions')
    partner_bank_ids = fields.One2many('res.partner.bank.contract', 'contract_id', string='RIB :')
    
    #Sous contrat
    parent_id = fields.Many2one("fleet.vehicle.contract","Contrat parent",compute="_compute_contract_parent_id",store=True)
    contract_childs = fields.Many2many("fleet.vehicle.contract","fleet_vehicle_contract_fleet_vehicle_contract_rel","contract_id","contract_id2","Sous Contrats",domain="[('contract_cd','=',False),('parent_id','=',False)]")
    
    @api.multi
    @api.depends("contract_childs")
    def _compute_contract_parent_id(self):
        for contract in self:
            if not isinstance(contract.id, int):
                continue
            self.env.cr.execute("update fleet_vehicle_contract set parent_id=null where parent_id=%s",(contract.id,))
            if contract.contract_childs.ids:
                self.env.cr.execute("update fleet_vehicle_contract set parent_id=%s where id in %s",(contract.id,tuple(contract.contract_childs.ids),))
        

    @api.multi
    def contract_print(self):
        """ Print the invoice and mark it as sent, so that we can see more
            easily the next step of the workflow
        """
        self.ensure_one()
        return self.env['report'].get_action(self, 'fleet.report_fleet_vehicle_contract')
    
     
    @api.onchange('src_agence_id')
    def onchange_src_agence_id(self):
        self.ret_src_agence_id = self.src_agence_id.id   

    @api.onchange('dest_agence_id')
    def onchange_dest_agence_id(self):
        self.ret_dest_agence_id = self.dest_agence_id.id   
    
    @api.onchange('ret_date', 'expiration_date')
    def change_for_lld_ret_ecart_jour(self):
        self.lld_ret_ecart_jour = 0
        if self.expiration_date and self.ret_date:
            date1 = fields.Datetime.from_string(self.expiration_date).date()
            date2 = fields.Datetime.from_string(self.ret_date).date()
            interval = date2 - date1
            self.lld_ret_ecart_jour = interval.days
    
    @api.one
    @api.depends("ret_diff_odometer","planned_odometer")
    def _compute_ret_ecart_km(self):
        self.ret_ecart_km = self.ret_diff_odometer - self.planned_odometer

    def compute_montant_loyer(self):
        for contract in self:
            contract.montant_loyer = 0
        if self.env.context.get('from_gantt'):
            from_gantt = dict(self.env.context.get('from_gantt'),res_id=self.id)
            return from_gantt

    @api.multi
    def _check_fuel(self) :
        for contract in self:
            if contract.fuel > 8:
                return False
        return True

    @api.multi
    def _check_expiration_date(self) :
        for contract in self:
            if contract.expiration_date < contract.start_date:
                return False
        return True

    @api.multi
    def _check_driver_age(self) :
        for contract in self:
            if not contract.contract_cd:
                continue
            min_age =  contract.company_id.min_age
            if contract.driver_id and contract.driver_id.age < min_age:
                return False
            for partner in contract.driver_ids:
                if partner.age < min_age:
                    return False
        return True

    @api.multi
    def _check_driver_permis(self) :
        for contract in self:
            if not contract.contract_cd:
                continue
            if contract.driver_id and not contract.driver_id.numero_permis:
                return False
            for partner in contract.driver_ids:
                if not partner.numero_permis:
                    return False
        return True


    _constraints = [(_check_fuel, 'Erreur : La valeur saisie pour le carburant doit être < 8 !', ['fuel']),
                    (_check_expiration_date, "Erreur : 'Retour prévu le' doit être > à 'Départ le'!", ['expiration_date']),
                    (_check_driver_age, "Erreur : L'âge minimum pour un conducteur n'est pas respecté!", ['driver_id','driver_ids']),
                    (_check_driver_permis, "Erreur : Numéro de permis non renseigné!", ['driver_id','driver_ids']),
                    ]


    @api.multi
    @api.returns('self', lambda value:value.id)
    def copy(self, default=None):
        prestation_ids = []
        partner_contact_ids = []
        partner_bank_ids = []
        contract = self
        for line in contract.prestation_ids:
            prestation_ids.append((0,0,{
                                        'product_id':line.product_id.id,
                                        'name': line.name,
                                        'product_qty':line.product_qty,
                                        'price_unit':line.price_unit,
                                        'ttc':line.ttc,
                                        'invoice_line_tax_ids':[(6,0,line.invoice_line_tax_ids.ids)],
                                        'date_start' : line.date_start,
                                        'date_stop':line.date_stop
                                        }))
        for contact in contract.partner_contact_ids:
            partner_contact_ids.append((0,0,{
                                        'type': contact.type,
                                        'phone': contact.phone,
                                        'name': contact.name,
                                        }))

        for rib_line in contract.partner_bank_ids:
            b = {'rib_id':rib_line.rib_id.id,'use':rib_line.use}
            partner_bank_ids.append((0,0,b))
            
        period = self.env['fleet.vehicle.contract.period'].find(default.get('start_date') or contract.start_date)
        default.update({
                        'prestation_ids':prestation_ids,
                        'partner_contact_ids' : partner_contact_ids,
                        'partner_bank_ids' : partner_bank_ids,
                        'contract_id' : False,
                        'contract_date_stop' :False,
                        'avenant_date_start' :False,
                        'period_id' : period[0].id,
                        'recurring_last_date' : False,
                        'ret_date' : False,
                        })
        return super(FleetVehicleContract,self).copy(default=default)


    @api.multi
    def create_move(self,contract,prev_move,odometer_start,start_date,expiration_date):
        context = self.env.context
        data_obj = self.env['ir.model.data']
        move = self.env["fleet.vehicle.move"]
        model, dispo_move_name_id = self.env['ir.model.data'].get_object_reference('fleet', 'fleet_vehicle_move_location0')
        model, loc_model_id = data_obj.get_object_reference('fleet', 'fleet_vehicle_move_location1')
        model, resa_model_id = data_obj.get_object_reference('fleet', 'fleet_vehicle_move_location10')
        if loc_model_id or resa_model_id:
            model, cd_model_id = data_obj.get_object_reference('fleet', 'fleet_vehicle_move_type_cd')
            model, ld_model_id = data_obj.get_object_reference('fleet', 'fleet_vehicle_move_type_ld')
            data = {
                    'name' :resa_model_id if contract.state=="devis" and contract.contract_cd else loc_model_id,
                    'vehicle_id':contract.vehicle_id.id, 'contract_id':contract.id,
                    'partner_id' : contract.partner_id.id, 'driver_id' : contract.driver_id.id,
                    'odometer_start' : odometer_start,
                    'odometer_end' :contract.ret_end_odometer,
                    'date_start':start_date,
                    'date_stop':expiration_date,
                    'src_agence_id' : contract.agence_id.id or contract.src_agence_id.id,
                    'dest_agence_id' : contract.ret_dest_agence_id.id or contract.dest_agence_id.id,
                    'doc_type_id' : cd_model_id if contract.contract_cd else ld_model_id,
                    }
            prev_move_name_id = prev_move.name.id
            if contract.vehicle_id:
                if context.get('prev_write_data'):
                    write_data = context.get('prev_write_data')
                    if isinstance(write_data, dict):
                        prev_move.write(write_data)
                elif start_date:
                    prec_date_stop = fields.Datetime.from_string(start_date)
                    if prev_move and contract.contract_cd:###Pour un contrat courte durée , un nouveau mouvement met fin au mouvement précédent
                        if dispo_move_name_id != prev_move_name_id: ### S'IL NE S'AGIT PAS D'UN MOUVEMENT DE DISPONIBILITÉ
                            prev_move.date_stop = prec_date_stop
                            prev_move.action_done()

                if dispo_move_name_id == prev_move_name_id: ### S'IL S'AGIT D'UN MOUVEMENT DE DISPONIBILITÉ
                    ###LES MOUVEMENT DE DISPONIBILITÉ ONT ÉTÉ CRÉÉS POUR AFFICHER LE MATERIEL DANS LE PLANNING
                    ###POUR LES MATÉRIELS N'AYANT AUCUN MOUVEMENT.DÉS LORS QU'ON CRÉÉ UN NOUVEAU MOUVEMENT , ON SUPPRIME
                    ###LE MOUVEMENT DE DISPONIBILITÉ
                    prev_move.unlink()
                    
                move = self.env['fleet.vehicle.move'].create(data)
                
                contract.vehicle_position_id = move.id


                
        return move
    
    def generate_contract_number(self,contract):
        if not contract.num_contract:
            contract.write({'num_contract':self.env['ir.sequence'].next_by_code('fleet.vehicle.contract')})
            
        model, model_id = self.env['ir.model.data'].get_object_reference('fleet', 'fleet_vehicle_move_location1')
        model, resa_model_id = self.env['ir.model.data'].get_object_reference('fleet', 'fleet_vehicle_move_location10')
        if model_id:
            prev_move = contract.vehicle_position_id
            if prev_move and (prev_move.name.id == resa_model_id) and prev_move.contract_id == contract:
                write_data = {
                              'name':model_id,
                              'date_start':contract.start_date,
                              'date_stop':contract.expiration_date,
                              'vehicle_id' : contract.vehicle_id.id,
                              'partner_id' : contract.partner_id.id,
                              'src_agence_id' : contract.src_agence_id.id or contract.agence_id.id,
                              'dest_agence_id' : contract.dest_agence_id.id
                              }
                prev_move.write(write_data)
            else:
                self.create_move(contract, prev_move, contract.vehicle_odometer, contract.start_date, contract.expiration_date)
        else:
            raise UserError(_(u'Erreur emplacement arrivé.'))

    def generate_devis_number(self,contract):
        if not contract.num_devis:
            contract.write({'num_devis':self.env['ir.sequence'].next_by_code('fleet.vehicle.contract.devis')})

    def generate_reservation_number(self, contract):
        if not contract.num_resa:
            contract.write({'num_resa':self.env['ir.sequence'].next_by_code('fleet.vehicle.contract.resa')})

        model, model_id = self.env['ir.model.data'].get_object_reference('fleet', 'fleet_vehicle_move_location10')
        if model_id:
            move = contract.vehicle_position_id
            self.create_move(contract, move, contract.vehicle_odometer, contract.start_date, contract.expiration_date)
        else:
            raise UserError(_(u'Erreur emplacement arrivé.'))
                    
    @api.model
    def create(self, vals):
        contract = super(FleetVehicleContract, self).create(vals)
        if 'state' not in vals or vals.get('state') == 'devis':
            self.generate_devis_number(contract)
        if self.env.context.get('auto_reservation'):
            if contract.contract_cd:
                contract.contract_reservation()
        if self.env.context.get('auto_contract'):
            contract.contract_open()
        return contract

    @api.multi
    def write(self, vals):
        move_vals = {}

        for c in self:
            if vals.get('start_date'):
                move_vals['date_start'] = vals.get('start_date')
            if vals.get('expiration_date'):
                move_vals['date_stop'] = vals.get('expiration_date')
            if vals.get('vehicle_id'):
                move_vals['vehicle_id'] = vals.get('vehicle_id')
            if vals.get('src_agence_id') or vals.get('agence_id'):
                move_vals['src_agence_id'] = vals.get('src_agence_id') or vals.get('agence_id')
            if vals.get('dest_agence_id'):
                move_vals['dest_agence_id'] = vals.get('dest_agence_id')
            if vals.get('partner_id'):
                move_vals['partner_id'] = vals.get('partner_id')    
            if not self.env.context.get('from_move_update'): ##PERMET D'ÉVITER UNE BOUCLE AVEC LA MISE À JOUR DES MOUVEMENTS       
                move = self.env['fleet.vehicle.move'].search([('contract_id','=',c.id)],order="id desc")
                if move:
                    move[0].write(move_vals)
        return super(FleetVehicleContract, self).write(vals)

    @api.multi
    def contract_reservation(self):
        for contract in self:
            if not contract.vehicle_id and not contract.booking:
                if contract.contract_cd:
                    raise UserError(_('Vous devez préciser le véhicule.'))
            self.generate_reservation_number(contract)
        self.write({'state': 'reservation'})
        if self.env.context.get('from_gantt'):
            from_gantt = dict(self.env.context.get('from_gantt'),res_id=self.id)
            return from_gantt
        return True

    @api.multi
    def contract_open(self):
        for contract in self:
            if not contract.vehicle_id:
                raise UserError(_('Vous devez préciser le véhicule.'))
            self.generate_contract_number(contract)
        
        self.write({'state': 'open'})
        if self.env.context.get('from_gantt'):
            from_gantt = dict(self.env.context.get('from_gantt'),res_id=self.id)
            return from_gantt
        return True
    
    @api.multi
    def contract_depart(self):
        self.write({'state': 'depart'})
        if self.env.context.get('from_gantt'):
            from_gantt = dict(self.env.context.get('from_gantt'),res_id=self.id)
            return from_gantt
        return True
    
    @api.multi
    def contract_closed(self):
        self.write({'state': 'closed'})
        if self.env.context.get('from_gantt'):
            from_gantt = dict(self.env.context.get('from_gantt'),res_id=self.id)
            return from_gantt
        return True


    @api.onchange('type_id')
    def onchange_type_id(self):
        #self.type_code = self.type_id.code
        self.contract_cd = self.type_id.contract_cd

            
    @api.onchange('vehicle_id')
    def onchange_vehicle_id(self):
        # if self.vehicle_id:
        self.vehicle_odometer = self.vehicle_id.odometer
        self.vehicle_license_plate = self.vehicle_id.license_plate
        self.vehicle_category_id = self.vehicle_id.category_id.id
            
        self.vehicle_position_id = self.vehicle_id.last_move_id.id
        self.vehicle_libelle = self.vehicle_id.libelle

        
    @api.onchange('partner_id')
    def onchange_partner_id(self):
        self.partner_name = self.partner_id.name
        self.partner_balance = self.partner_id.partner_balance
        self.payment_mode_id = self.partner_id.customer_payment_mode_id.id
        self.property_payment_term_id = self.partner_id.property_payment_term_id.id
        self.ref = self.partner_id.ref
        if self.partner_id.driver:
            if not self.driver_id:
                self.driver_id = self.partner_id.id
        bank_ids = []
        for rib in self.partner_id.bank_ids:
            b = rib.read([])
            if len(b)>0:
                b[0].update({'rib_id':rib.id})
                bank_ids.append((0,0,b[0]))
        self.partner_bank_ids = bank_ids
        


    @api.onchange('nombre_jour','lld_nombre_mois', 'start_date')
    def onchange_params_expiration_date(self):
        if self.start_date:
            if self.contract_cd:
                interval = timedelta(days=int(self.nombre_jour))
                self.expiration_date = fields.Datetime.from_string(self.start_date) + interval
            else:
                interval = relativedelta.relativedelta(months=int(self.lld_nombre_mois) or 0)
                self.expiration_date = fields.Datetime.from_string(self.start_date) + interval
                self.onchange_frequency()

    @api.onchange('frequency')
    def onchange_frequency(self):
        if self.recurring_last_date:
            last_date = fields.Date.from_string(self.recurring_last_date)
        else:
            last_date = fields.Date.from_string(self.start_date) + relativedelta.relativedelta(months=-1)
        
        new_date = False
        if self.frequency == "monthly":
            new_date = last_date+relativedelta.relativedelta(months=+1)
        elif self.frequency == "3monthly":
            new_date = last_date+relativedelta.relativedelta(months=+1*3)
        elif self.frequency == "6monthly":
            new_date = last_date+relativedelta.relativedelta(months=+1*6)
        elif self.frequency == "12monthly":
            new_date = last_date+relativedelta.relativedelta(months=+1*12)
            
        if new_date:
            new_period = self.env['fleet.vehicle.contract.period'].find(new_date)
            self.period_id = new_period[0].id

    @api.onchange('recurring_last_date')
    def onchange_recurring_last_date(self):
        self.onchange_frequency()

    @api.onchange('expiration_date')
    def onchange_expiration_date(self):
        if self.expiration_date < self.start_date:
            raise UserError(_("Erreur : 'Retour prévu le' doit être > à 'Départ le'!."))


    @api.multi
    def return_action_to_open(self):
        """ This opens the xml view specified in xml_id for the current vehicle """
        self.ensure_one()
        xml_id = self.env.context.get('xml_id')
        if xml_id:
            res = self.env['ir.actions.act_window'].for_xml_id('fleet', xml_id)
            context = dict(self.env.context)
            contract = self
            partner_id = contract.partner_id.id
            context.update({
                        'default_contract_id': contract.id,
                        'default_src_agence_id':contract.agence_id.id or contract.src_agence_id.id ,
                        'default_dest_agence_id':contract.ret_dest_agence_id.id or contract.dest_agence_id.id ,
                        'default_agence_id':contract.agence_id.id or contract.src_agence_id.id ,
                        'default_vehicle_id':contract.vehicle_id.id,
                        'default_partner_id':partner_id,
                        'default_company_id':contract.company_id.id
                        })
            res.update(
                context=context,
                domain=[('contract_id', '=', self.id)]
            )
            return res
        return False
    
    @api.multi
    def return_action_to_open_r(self):
        """ This opens the xml view specified in xml_id for the current vehicle """
        self.ensure_one()
        xml_id = self.env.context.get('xml_id')
        if xml_id:
            res = self.env['ir.actions.act_window'].for_xml_id('fleet', xml_id)
            return res
        return False

    @api.multi
    def view_fiche_r(self):
        '''
        This function returns an action that display existing invoices of given sales order ids. It can either be a in a list or in a form view, if there is only one invoice to show.
        '''
        self.ensure_one()
        xml_id = self.env.context.get('xml_id')
        r_obj = self.env['fleet.vehicle.contract.stop']
        mod_obj = self.env['ir.model.data']
        act_obj = self.env['ir.actions.act_window']
        
        contract = self

        result = act_obj.for_xml_id('fleet', xml_id)

        #compute the number of invoices to display
        rs = r_obj.search([('contract_id','=',contract.id)])
        
        res = mod_obj.get_object_reference('fleet', 'fleet_vehicle_contract_stop_form')
        views = [(res and res[1] or False, 'form')]
        res_id = rs.ids and rs.ids[0] or False
        result.update(
                views=views,
                res_id=res_id
                )
        return result
    
    @api.multi
    def view_invoices(self):
        '''
        This function returns an action that display existing invoices of given sales order ids. It can either be a in a list or in a form view, if there is only one invoice to show.
        '''
        self.ensure_one()
        xml_id = self.env.context.get('xml_id')
        invoice_obj = self.env['account.invoice']
        invoice_line_obj = self.env['account.invoice.line']
        mod_obj = self.env['ir.model.data']
        act_obj = self.env['ir.actions.act_window']
        
        contract = self
        context = {'default_contract_id': contract.id,'default_vehicle_id':contract.vehicle_id.id}
        if contract.contract_cd:
            model,type_facture_id = mod_obj.get_object_reference('account','account_invoice_type_CD')
            context.update({
                        'default_partner_id':contract.partner_id.id,
                        'agence_id':contract.src_agence_id.id,
                        'default_type_facture_id':type_facture_id
                        })
        else:
            model,type_facture_id = mod_obj.get_object_reference('account','account_invoice_type_LD')
            context.update({
                        'default_partner_id':contract.partner_id.id,
                        'agence_id':contract.agence_id.id,
                        'default_type_facture_id':type_facture_id
                        })  

        result = act_obj.for_xml_id('account', xml_id)

        #compute the number of invoices to display
        invs = invoice_obj.search([('contract_id','=',contract.id),('type', 'in', ('out_invoice', 'out_refund'))])
        inv_lines=invoice_line_obj.search([('contract_id','=',contract.id),('invoice_id.type', 'in', ('out_invoice', 'out_refund'))])
        
        inv_ids = invs.ids
        for inv_line in inv_lines:
            inv_ids.append(inv_line.invoice_id.id)
        #choose the view_mode accordingly
        #if len(invs)>1:
        domain = "[('id','in',["+','.join(map(str, inv_ids))+"])]"
        #else:
            #res = mod_obj.get_object_reference('account', 'invoice_form')
            #views = [(res and res[1] or False, 'form')]
            #res_id = invs.ids and invs.ids[0] or False
        result.update(
                context=context,
                domain=domain
                )
        return result


    @api.multi
    def get_update_cumulative(self):
        for contract in self:
            last_fuel_variation = 0  ## CETTE VARIABLE PERMET DE EN CAS DE VALIDATION DU RETOUR DE L'ENGIN AVEC LA SAISIE DES CARBURANTS DEPART ET RETOUR D'EXCLURE LA VARIATION DE CARBURANT DE LA DERNIERE MACHINE AFFECTÉE AU CONTRAT
            total_odometer = 0
            total_fuel_qty = 0
            total_odometer_relay = 0
            for line in contract.contract_vehicle_ids:
                last_fuel_variation = line.fuel_variation
                total_fuel_qty += line.fuel_variation
                if line.odometer_variation > 0:
                    total_odometer+=line.odometer_variation
                    if not line.special:
                        total_odometer_relay +=line.odometer_variation
            if contract.return_ok:
                total_fuel_qty += (contract.ret_fuel1 - contract.ret_fuel2) - last_fuel_variation
            contract.write({'total_odometer':total_odometer,'total_fuel_qty':total_fuel_qty,'total_odometer_relay':total_odometer_relay})
        if self.env.context.get('from_gantt'):
            from_gantt = dict(self.env.context.get('from_gantt'),res_id=self.id)
            return from_gantt
        return True



    @api.multi
    def get_update_price(self):
        for contract in self:
            contract.compute_line()
        if self.env.context.get('from_gantt'):
            from_gantt = dict(self.env.context.get('from_gantt'),res_id=self.id)
            return from_gantt
        return True

    @api.multi
    def get_update_price2(self):
        data_obj = self.env['ir.model.data']
        model, product_days_sup_id = data_obj.get_object_reference('product', 'product_product1')
        model, product_kms_sup_id = data_obj.get_object_reference('product', 'product_product5')
        for contract in self:
            contract.compute_line()
            J_SUP = 0
            KMS_SUP = contract.ret_diff_odometer - contract.planned_odometer
            if not contract.expiration_date or not contract.ret_date:
                raise UserError(_("Les données du retour n'ont pas été correctement saisies."))
            if contract.expiration_date and contract.ret_date:
                date1 = fields.Datetime.from_string(contract.expiration_date).date()
                date2 = fields.Datetime.from_string(contract.ret_date).date()
                diff = date2 - date1
                J_SUP = diff.days
            for line in contract.prestation_ids:
                if line.product_id.id == product_days_sup_id:
                    line.write({'product_qty':J_SUP + line.product_qty})
                if line.product_id.id == product_kms_sup_id:
                    line.write({'product_qty':KMS_SUP + line.product_qty})
            contract.return_ok = True
            self.env['fleet.vehicle.odometer'].create({'vehicle_id':contract.vehicle_id.id,'value':contract.ret_end_odometer,'date':contract.ret_date,'origin':'contract'})
        if self.env.context.get('from_gantt'):
            from_gantt = dict(self.env.context.get('from_gantt'),res_id=self.id)
            return from_gantt
        return True
    

    def compute_line(self):
        prestation_obj = self.env['fleet.vehicle.contract.prestation']
        data_obj  = self.env['ir.model.data']
        model, product_days_id = data_obj.get_object_reference('product', 'product_product0')
        model, product_days_sup_id = data_obj.get_object_reference('product', 'product_product1')
        model, product_kms_id = data_obj.get_object_reference('product', 'product_product4')
        model, product_kms_sup_id = data_obj.get_object_reference('product', 'product_product5')
        
        prestation_obj.search([('id', 'in', self.prestation_ids.ids), ('auto', '=', True)]).unlink()
        
        data_days = data_days_sup = data_kms = data_kms_sup = {}
        
        if self.item_id.forfait_days > 0:
            days_sup = self.nombre_jour - self.item_id.forfait_days
            data_days = {
                    'product_qty' : self.item_id.forfait_days,
                    'contract_id' : self.id,
                    'auto' : True,
                    }
            data_kms = {
                    'product_qty' : self.item_id.forfait_days * self.item_id.forfait_kms,
                    'contract_id' : self.id,
                    'auto' : True,
                    }
            if days_sup > 0:
                data_days_sup = {
                                'product_qty' : days_sup,
                                'contract_id' : self.id,
                                'auto' : True,
                                }
                data_kms_sup = {
                                'product_qty' : days_sup * self.item_id.forfait_days_kms,
                                'contract_id' : self.id,
                                'auto' : True,
                                }
        for line in self.item_id.line_ids:
                                                                                     
            data = {
                    'product_id' : line.product_id.id,
                    'name' : line.product_id.name,
                    'price_unit' : line.price_unit,
                    'ttc' : line.ttc,
                    'product_qty' : self.nombre_jour if line.product_id.id == product_days_id else 0,
                    'contract_id' : self.id,
                    'auto' : True,
                    }
            invoice_line_tax_ids = line.product_id.taxes_id.ids

            data.update({"invoice_line_tax_ids":[(6, 0, invoice_line_tax_ids)]})
            
            if line.product_id.id == product_days_id:
                data.update(data_days)
            elif line.product_id.id == product_days_sup_id:
                data.update(data_days_sup)
            elif line.product_id.id == product_kms_id:
                data.update(data_kms)
            elif line.product_id.id == product_kms_sup_id:
                data.update(data_kms_sup)
            else:
                data.update({'product_qty':1})
            
            if data.get('product_qty') != 0:
                presta = prestation_obj.create(data)
                presta.get_apply_yield()
        return True

    @api.multi
    def get_calculate_price(self):
        self.ensure_one()
        item_obj = self.env['product.pricelist.item']
        for contract in self:
            domain1 = [('vehicle_categ_id', '=', contract.category_id.id), ('days_min', '<=', contract.nombre_jour), ('days_max', '>=', contract.nombre_jour)]
            domain2 = [('vehicle_categ_id', '=', contract.category_id.id), ('kms_min', '<=', contract.planned_odometer), ('kms_max', '>=', contract.planned_odometer)]
            domain3 = [('id','in',self.ids),('vehicle_categ_id','=',contract.category_id.id),('unlimited_mileage','=',True)]
            
            item_ids1 = item_obj.search(domain1).ids
            item_ids2 = item_obj.search(domain2).ids
            item_ids3 = item_obj.search(domain3).ids
            
            
            item_ids2.extend(item_ids3)
            item_ids = list(set(item_ids1).intersection(item_ids2))
            if len(item_ids) == 0:
                contract.write({
                                'item_id':False,'pricelist_id':False})
            else:
                item = item_obj.browse(item_ids[0])
                contract.write({'item_id':item.id,'pricelist_id':item.pricelist_id.id})
            

            contract.compute_line()
        
        if self.env.context.get('from_gantt'):
            from_gantt = dict(self.env.context.get('from_gantt'),res_id=self.id)
            return from_gantt
        
        return True

    def _prepare_invoice_data(self,contract):
        model,type_id = self.env['ir.model.data'].get_object_reference('account','account_invoice_type_LD')

        journal_obj = self.env['account.journal']

        if not contract.partner_id:
            raise UserError(_("You must first select a Customer for Contract %s!") % contract.name )

        fpos = contract.partner_id.property_account_position_id or False
        journal_ids = journal_obj.search([('type', '=','sale'),('company_id', '=', contract.company_id.id or False)], limit=1)
        if not journal_ids:
            raise UserError(_('Please define a sale journal for the company "%s".') % (contract.company_id.name or '', ))

        partner_payment_term_id = contract.property_payment_term_id.id

        currency_id = False
        
        if contract.partner_id.property_product_pricelist:
            currency_id = contract.partner_id.property_product_pricelist.currency_id.id
        elif contract.company_id:
            currency_id = contract.company_id.currency_id.id

        partner_bank_id = False
        c_ban_obj = self.env['res.partner.bank.contract']
        bank_lines = c_ban_obj.search([('contract_id','=',contract.id)],order="use desc,sequence asc")
        if bank_lines:
            partner_bank_id = bank_lines[0].rib_id.id
        invoice = {
                   'account_id': contract.partner_id.property_account_receivable_id.id,
                   'partner_bank_id' : partner_bank_id,
                   'type': 'out_invoice',
                   'partner_id': contract.partner_id.id,
                   'currency_id': currency_id,
                   'journal_id': len(journal_ids) and journal_ids[0].id or False,
                   'origin': contract.name,
                   'fiscal_position_id': fpos and fpos.id,
                   'payment_term_id': partner_payment_term_id,
                   'payment_mode_id' : contract.payment_mode_id.id,
                   'company_id': contract.company_id.id or False,
                   'vehicle_id' : contract.vehicle_id.id,
                   'contract_id' : contract.id,
                   'type_facture_id' : type_id,
                   'agence_id' : contract.agence_id.id,
                   }
        return invoice


    
    
    def _prepare_invoice_lines(self,contract,date_start,date_stop):
        invoice_lines = []
        for line in contract.prestation_ids:
            ####DEBUT ALGORITHME DE GESTION DES DATES D'EXPIRATIONS
            ###Traiter l'erreur liéé à date_start=False or date_stop=False
            invoice_line_date_start=  date_start
            invoice_line_date_stop=  date_stop
            if line.date_start and line.date_stop:
                pres_date_start=  fields.Date.from_string(line.date_start)
                pres_date_stop=  fields.Date.from_string(line.date_stop)
            
                if pres_date_start > invoice_line_date_stop:
                    continue
                elif pres_date_stop < invoice_line_date_start:
                    continue
                else:
                    if pres_date_start >= invoice_line_date_start and pres_date_start <= invoice_line_date_stop:
                        invoice_line_date_start = pres_date_start
                        if pres_date_stop <= invoice_line_date_stop:
                            invoice_line_date_stop = pres_date_stop
                    elif pres_date_stop >= invoice_line_date_start:
                        if pres_date_stop <= invoice_line_date_stop:
                            invoice_line_date_stop = pres_date_stop
            ####FIN ALGORITHME DE GESTION DES DATES D'EXPIRATIONS
            
            price_unit = line.price_untaxed
            
            prorata = self.get_product_prorata(contract, line.product_id, invoice_line_date_start, invoice_line_date_stop)

            res = line.product_id
            account_id = line.account_id.id
            
            if not account_id:
                account_id = res.categ_id.property_account_income_categ_id.id


            invoice_lines.append((0, 0, {
                'name': line.name,
                'account_id': account_id,
                'price_unit': price_unit*prorata,
                'quantity': line.product_qty,
                'product_id': res.id or False,
                'invoice_line_tax_ids': [(6, 0, line.invoice_line_tax_ids.ids)],
                'discount' : line.discount,
                'contract_date_start' : invoice_line_date_start,
                'contract_date_end' :invoice_line_date_stop,
                'contract_id' : contract.id,
                'vehicle_id' : contract.vehicle_id.id,
                'agence_id' : contract.agence_id.id,
            }))
        km_sup_invoice_line = self.get_km_sup_values(contract,date_start,date_stop)
        if km_sup_invoice_line.get('product_id') and km_sup_invoice_line.get('quantity') > 0:
            invoice_lines.append((0,0,km_sup_invoice_line))
        return invoice_lines

    def get_km_sup_values(self,contract,date_start,date_stop):
        invoice_line_data  ={'product_id':False,'quantity':0}
        line_obj = self.env['fleet.vehicle.contract.odometer.line']
        domain = [('contract_id','=',contract.id),
                  ('contract_odometer_id.frequency','=',contract.km_frequency),
                  ('date_start','<=',date_start),
                  ('date_stop','>=',date_stop)]
        lines  = line_obj.search(domain)
        if lines:
            product = lines[0].contract_odometer_id.product_id
            fpos = contract.partner_id.property_account_position_id
            account = product.property_account_income_id or product.categ_id.property_account_income_categ_id
            account = fpos.map_account(account)

            invoice_line_tax_ids = self.env['account.fiscal.position'].map_tax(fpos, product.taxes_id)
        
            prorata = self.get_product_prorata(contract, product, date_start, date_stop)
            used_km = lines[0].odometer_stop - lines[0].odometer_start
            autorised_km = contract.km_ecart
            if contract.lld_nombre_mois > 0:
                autorised_km += contract.planned_odometer / contract.lld_nombre_mois
            
            km_sup_qty = used_km - autorised_km
                
            invoice_line_data.update({
                                      'name' : product.name,
                                      'product_id':product.id,
                                      'quantity' : km_sup_qty,
                                      'price_unit' : contract.km_sup_price_unit*prorata,
                                      'account_id' : account.id,
                                      'invoice_line_tax_ids': [(6,0,invoice_line_tax_ids)],
                                      'contract_date_start' : date_start,
                                      'contract_date_end' :date_stop,
                                      'contract_id' : contract.id,
                                      'vehicle_id' : contract.vehicle_id.id,
                                      'agence_id' : contract.agence_id.id,
                                      })
        return invoice_line_data

    
    def get_product_prorata(self,contract,product,date_start,date_stop):
        total_prorata = 0
        prorata = 1
        if product.prorata:
            go = True
            date_debut = date_start
            while go:
                date_debut_split  = str(date_debut).split("-")
                calendar_data  =calendar.monthrange(int(date_debut_split[0]),int(date_debut_split[1]))
                date_fin = date_debut_split[0]+"-"+date_debut_split[1]+"-"+str(calendar_data[1])
                date_fin = fields.Date.from_string(date_fin)
                if date_fin >= date_stop:
                    date_fin = date_stop
                    go = False
                if contract.frequency_type == 'real':
                    prorata = float(((date_fin - date_debut).days)+1) / float(calendar_data[1]) ## calcul calendaire
                elif contract.frequency_type == 'no_prorata':
                    prorata = 1
                else:
                    prorata = float(((date_fin - date_debut).days)+1) / 30
                    if prorata > 1:
                        prorata = 1
                    else:
                        ###Principalement pour le mois de février ce bout de code sera exécuter pour changer le prorata
                        date_end_split  = str(date_stop).split("-")
                        contract_first_day = str(date_start).split("-")[2]
                        contract_last_day = date_end_split[2]
                        calendar_data  =calendar.monthrange(int(date_end_split[0]),int(date_end_split[1]))
                        month_last_day = calendar_data[1]
                        if int(contract_first_day) == 1 and int(contract_last_day) == int(month_last_day):
                            prorata = 1
                
                date_debut = date_fin + relativedelta.relativedelta(days=1)
                total_prorata +=prorata
        else:
            total_prorata = prorata
        return total_prorata
    

    
    def _prepare_invoice(self,contract,date_start,date_end):
        invoice = self._prepare_invoice_data(contract)
        invoice['invoice_line_ids'] = self._prepare_invoice_lines(contract,date_start,date_end)
        return invoice

    @api.model
    def _cron_recurring_create_invoice(self):
        return self._recurring_create_invoice(automatic=True)
    
    @api.multi
    def _recurring_create_invoice(self,date_invoice=False,wizard_period_id=False,validate_invoices=False,automatic=False):
        all_invoices_data = []
        avenants = []
        for contract in self:
            ret_date_ok = False
            avenant_date_ok = False
            while True:  ###Faire une boucle pour créer toutes les factures du contrat jusqu'à atteindre la date de facture demandée
                #### Debut Première condition d'arrêt
                wizard_period  = self.env['fleet.vehicle.contract.period'].browse(wizard_period_id)
                if contract.period_id.date_start >= wizard_period.date_stop:
                    break
                #### Fin Première condition d'arrêt
                contract_write_data = {}
                date_start = fields.Datetime.from_string(contract.start_date).date()
                if contract.recurring_last_date:
                    date_start = fields.Date.from_string(contract.recurring_last_date) + relativedelta.relativedelta(days=1)
                date_end = fields.Date.from_string(contract.period_id.date_stop)
            
                if contract.contract_date_stop:
                    contract_date_stop = fields.Date.from_string(contract.contract_date_stop)
                    if date_end >= contract_date_stop:
                        avenant_date_ok = True  ##Ce paramètre permet d'arreter la facturation pour un contrat au mois de retour du véhicule qui est précisé dans l'onglet "Retour"
                        avenants.append(contract.contract_id)
                        date_end = contract_date_stop
                
                if contract.ret_date and not avenant_date_ok:
                    ret_date= fields.Datetime.from_string(contract.ret_date).date()
                    if date_end >= ret_date:
                        ret_date_ok = True  ##Ce paramètre permet d'arreter la facturation pour un contrat au mois de retour du véhicule qui est précisé dans l'onglet "Retour"
                        date_end = ret_date
                        
                if date_end < date_start:
                    raise UserError(_("Une erreur a été constatée au niveau des dates du contract: '%s'.La prochaine période à facturer n'est pas correcte.Vous l'avez peut-être modifiée manuellement.")%(contract.name,))
                try:
                    
                    invoice_values = self._prepare_invoice(contract,date_start,date_end)
                    invoice_values.update(
                                      {'date_invoice':date_invoice,
                                       'contract_period_id':contract.period_id.id,
                                       'contract_date_start':date_start,
                                       'contract_date_end' :date_end
                                       }
                                     )
                    all_invoices_data.append(invoice_values)
                    if contract.frequency == "monthly":
                        new_date = date_end+relativedelta.relativedelta(months=+1)
                    elif contract.frequency == "3monthly":
                        new_date = date_end+relativedelta.relativedelta(months=+1*3)
                    elif contract.frequency == "6monthly":
                        new_date = date_end+relativedelta.relativedelta(months=+1*6)
                    elif contract.frequency == "12monthly":
                        new_date = date_end+relativedelta.relativedelta(months=+1*12)
                    new_period = self.env['fleet.vehicle.contract.period'].find(new_date)
                    new_period_id = new_period and new_period[0].id
                    contract_write_data.update({'recurring_last_date': date_end.strftime('%Y-%m-%d'),'period_id':new_period_id})
                    contract.write(contract_write_data)
                    
                    if automatic:
                        self.env.cr.commit()
                except Exception:
                    if automatic:
                        self.env.cr.rollback()
                        _logger.exception('Fail to create recurring invoice for contract %s', contract.name)
                    else:
                        raise

                if avenant_date_ok:##ARRETER LA BOUCLE CAR LA DATE DE L'ACTIVATION DE L'AVENANT EST ARRIVÉE
                    contract.write({'state': 'closed'})
                    break                    
                if ret_date_ok:##ARRETER LA BOUCLE CAR MOIS DATE DE RETOUR CORRESPOND AU MOIS EN COURS
                    contract.write({'state': 'closed'})
                    break
        invoices = self.action_invoice_create(all_invoices_data,date_invoice,wizard_period_id)
        for invoice in invoices:
            #### Début évènement changement type de facture et condition de règlement
            if validate_invoices : 
                invoice.action_invoice_open()
            #### Fin évènement changement type de facture et condition de règlement
        ######ACTIVATION DES AVENANTS:
        if avenants:
            avenants.write({"state":"open"})
            ret_dict = avenants. _recurring_create_invoice(date_invoice=date_invoice,wizard_period_id=wizard_period_id,validate_invoices=validate_invoices,automatic=automatic)
            invoices.extend(ret_dict.get('invoices'))
        return {'invoices':invoices}

    def action_invoice_create(self,invoices_data,date_invoice,period_id):
        invoice_obj = self.env['account.invoice']
        todo = {}
        extra_partner_invoice_data = []
        invoices = []
        base_extra_partners = self.env['res.partner'].search([('invoice_grouped','=',True)])
        for invoice_data in invoices_data:
            if invoice_data.get('partner_id') in base_extra_partners.ids:
                extra_partner_invoice_data.append(invoice_data)
            else:
                invoice = invoice_obj.create(invoice_data)
                invoices.append(invoice)
                
        
        for extra_invoice_data in extra_partner_invoice_data:
            invoice_line_ids = extra_invoice_data.get('invoice_line_ids')
            key = extra_invoice_data.get('partner_id'),extra_invoice_data.get('payment_term_id'),extra_invoice_data.get('payment_mode_id')
            extra_invoice_data.update({
                                 'date_invoice':date_invoice,
                                 })
            extra_invoice_data2 = extra_invoice_data  #Faire ainsi pour ne pas altérer l'information initiale
            extra_invoice_data2.update({'invoice_line_ids':[]})##A l'initialisation , il n'ya aucune ligne de facture
            todo.setdefault(key,extra_invoice_data2)
            todo[key]['invoice_line_ids'].extend(invoice_line_ids)
            if extra_invoice_data.get('contract_date_end') > todo[key].get('contract_date_end'):
                todo[key].update({"contract_date_end":extra_invoice_data['contract_date_end']})
            if todo[key].get('origin'):
                todo[key]['origin'] += "|"+extra_invoice_data['origin']
            else:
                todo[key]['origin'] = extra_invoice_data['origin']
        
        for grouped_invoice_data in todo.values():
            origin = grouped_invoice_data.get('origin')
            origin_split = origin.split("|")
            origin_split = set(origin_split)
            origin = "|".join(origin_split)
            grouped_invoice_data.update({
                                 'contract_id':False,
                                 'vehicle_id' : False,
                                 'agence_id':False,
                                 'origin' : origin,
                                 })
            invoice = invoice_obj.create(grouped_invoice_data)
            invoices.append(invoice)
        return invoices

    @api.multi
    def unlink(self):
        for contrat in self:
            if contrat.state in ('open', 'closed'):
                raise UserError(_(u'Vous ne pouvez pas supprimer un contrat ouvert ou clos.'))
        return super(FleetVehicleContract, self).unlink()


class FleetVehicleContractType(models.Model):
    _name = 'fleet.vehicle.contract.type'
    
    code = fields.Char('Code', required=True)
    name = fields.Char('Nom', required=True)
    contract_cd = fields.Boolean('Contrat courte durée')

    @api.multi
    def name_get(self):
        result = []
        for rec in self:
            name = rec.name
            result.append((rec.id,name))
        return result

    @api.multi
    def unlink(self):
        for type_contrat in self:
            if type_contrat.code in ('LCD', 'LLD'):
                raise UserError(_(u'Type de contrat principal.'))
        return super(FleetVehicleContractType, self).unlink()


class FleetVehicleContractContact(models.Model):

    _name = 'fleet.vehicle.contract.contact'

    name = fields.Char('Nom', required=True)
    prenom = fields.Char('Prenom')
    type = fields.Char('Type')
    phone = fields.Char('Numéro')
    contract_id = fields.Many2one('fleet.vehicle.contract', 'Contrat courte durée')
    lld_contract_id = fields.Many2one('fleet.vehicle.contract', 'Contrat longue durée')

   

class FleetVehicleContractPrestation(models.Model):

    def get_sum_tax(self,taxes):
        sum_tax = 0
        for tax in taxes:
            if tax.amount_type == 'percent':
                sum_tax += tax.amount
            else :
                return -1
        
        return sum_tax / 100

    @api.one
    @api.depends('contract_id.currency_id','price_unit','invoice_line_tax_ids','product_qty','ttc','discount')
    def _amount_line(self):
        
        invoice_line_taxes = self.invoice_line_tax_ids
        price = self.price_unit * (1 - (self.discount or 0.0) / 100.0)
        if self.ttc:
            sum_tax = self.get_sum_tax(invoice_line_taxes)
            if sum_tax == -1:
                raise UserError(_("Erreur de configuration de la taxe.Vous avez indiqué que la taxe est incluse dans le prix.Mais la configuration de la taxe ne permet pas le calcul du prix unitaire hors taxe."))
                
            amount_untaxed = (price*self.product_qty) / (1 + sum_tax)
            amount_total = price*self.product_qty
            amount_tax = amount_total - amount_untaxed 
        else:
            all_amount = self.invoice_line_tax_ids.compute_all(price,currency=self.contract_id.currency_id,
                                                                  quantity=self.product_qty, product=self.product_id, partner=self.contract_id.partner_id)
            amount_tax = 0
            for tax in all_amount['taxes']:
                amount_tax += tax['amount']
            amount_untaxed = all_amount['total_excluded']
            amount_tax = amount_tax
            amount_total = all_amount['total_included']
            
            
        self.amount_untaxed = amount_untaxed
        self.amount_tax = amount_tax
        self.amount_total = amount_total
            
    @api.one
    @api.depends('contract_id.currency_id','price_unit','invoice_line_tax_ids','product_qty','ttc','discount')
    def _get_price_untaxed(self):
        price_untaxed = 0
        price = self.price_unit
        invoice_line_taxes =self.invoice_line_tax_ids
        if self.ttc:
            sum_tax = self.get_sum_tax(invoice_line_taxes)
            if sum_tax == -1:
                raise UserError(_("Erreur de configuration de la taxe.Vous avez indiqué que la taxe est incluse dans le prix.Mais la configuration de la taxe ne permet pas le calcul du prix unitaire hors taxe."))
                
            price_untaxed = (price) / (1 + sum_tax)
            
        else:

            all_amount = self.invoice_line_tax_ids.compute_all(price,currency=self.contract_id.currency_id,
                                                                  quantity=self.product_qty, product=self.product_id, partner=self.contract_id.partner_id)
            
            if self.product_qty > 0:
                price_untaxed = all_amount['total_excluded'] / self.product_qty
                
        self.price_untaxed = price_untaxed


    @api.model
    def _default_account(self):
        journal_obj = self.env['account.journal']
        journals = journal_obj.search([('type', '=', "sale")])
        if journals:
            journal = journals[0]
            return journal.default_credit_account_id.id
        
    _name = 'fleet.vehicle.contract.prestation'
    _description = 'Ligne de prestation'
    _order = "auto desc,id asc"
    
    auto = fields.Boolean('Créer par le système')
    contract_id = fields.Many2one('fleet.vehicle.contract', 'Contract')
    contract_cd = fields.Boolean(related='contract_id.contract_cd',string='Contrat CD')
    driver_contract_id = fields.Many2one('fleet.vehicle.contract', 'Contract conducteur')
    vehicle_id = fields.Many2one("fleet.vehicle",related='contract_id.vehicle_id',string='Parc', readonly=True)
    product_id = fields.Many2one('product.product', 'Prestation', required=True)
    name = fields.Text('Libellé', required=True)
    account_id = fields.Many2one('account.account', string='Compte',
                                       required=True,default=_default_account)
    price_unit = fields.Float('Prix unitaire', required=True)
    discount = fields.Float('Remise (%)')
    product_qty = fields.Float('Quantité', required=True,default=1)
    invoice_line_tax_ids = fields.Many2many('account.tax',
                                           'contract_prestation_line_tax', 'invoice_line_id', 'tax_id',string='Taxes')
    ttc = fields.Boolean('TTC')
    date_start = fields.Date('Début')
    date_stop = fields.Date('Fin')
    yield_id = fields.Many2one('product.price.yield','Tarif Yield')
    price_untaxed = fields.Float(compute="_get_price_untaxed", string='Montant unitaire hors taxe',store=True)
    amount_untaxed = fields.Float(compute="_amount_line", string='Montant HT',store=True)
    amount_tax = fields.Float(compute="_amount_line", string='Montant TVA', store=True)
    amount_total = fields.Float(compute="_amount_line", string='Montant TTC',store=True)

    @api.onchange("product_id")
    def product_id_change(self):
        c1 = self.product_id.property_account_income_id
        c2 = self.product_id.categ_id.property_account_income_categ_id
        if c1 or c2:
            self.account_id = c1.id or c2.id
        self.name = self.product_id.name
    
    @api.multi
    def get_apply_yield(self):
        for line in self:
            company_id  = line.contract_id.company_id.id
            agence_id  = line.contract_id.src_agence_id.id
            company_type  = line.contract_id.partner_id.company_type
            partner_id  = line.contract_id.partner_id.id
            category_id  = line.contract_id.category_id.id
            product_id  = line.product_id.id
            date = line.contract_id.start_date
            ###l'ordre par article decroissant sachant que les lignes ont le même article
            self._cr.execute(
                'SELECT item.id '
                'FROM product_price_yield AS item '
                'WHERE (item.company_id IS NULL OR item.company_id = %s)'
                'AND (item.agence_id IS NULL OR item.agence_id = %s)'
                'AND (item.company_type IS NULL OR item.company_type = %s)'
                'AND (item.partner_id IS NULL OR item.partner_id = %s)'
                'AND (item.category_id IS NULL OR item.category_id = %s)'
                'AND (item.product_id IS NULL OR item.product_id = %s)'
                'AND (item.date_start IS NULL OR item.date_start<=%s) '
                'AND (item.date_stop IS NULL OR item.date_stop>=%s)'
                'ORDER BY item.id desc',
            (company_id or 0, agence_id or 0, company_type, partner_id,category_id or 0,product_id or 0, date, date))
            item_ids = [x[0] for x in self._cr.fetchall()]
            items = self.env['product.price.yield'].browse(item_ids)
            if items:
                new_price = line.price_unit*(1+items[0].rate/100)
                line.price_unit = new_price
                line.yield_id = items[0].id


class FleetVehicleContractOdometer(models.Model):
    _name='fleet.vehicle.contract.odometer'


    @api.model
    def _get_date_start(self):
        period_obj = self.env['fleet.vehicle.contract.period']
        period_ids = period_obj.find()
        period = period_ids[0]
        return period.date_start
    
    @api.model
    def _get_date_stop(self):
        period_obj = self.env['fleet.vehicle.contract.period']
        period_ids = period_obj.find()
        period = period_ids[0]
        return period.date_stop
    
    name = fields.Char('Référence',default="/")
    frequency = fields.Selection(FREQUENCY_SELECTION, "Périodicité",required=True)
    date_start = fields.Date('Période début',required=True,default=_get_date_start)
    date_stop = fields.Date('Période fin',required=True,default=_get_date_stop)
    product_id = fields.Many2one('product.product','Prestation',required=True,domain=[('prestation_ok','=',True)])
        
    line_ids = fields.One2many('fleet.vehicle.contract.odometer.line','contract_odometer_id','Lignes')


    
    @api.model
    def create(self,vals):
        if vals.get('name', '/') == '/':
            vals['name'] = self.env['ir.sequence'].next_by_code('fleet.vehicle.contract.odometer') or '/'
        return super(FleetVehicleContractOdometer, self).create(vals)

    @api.multi
    @api.returns('self', lambda value:value.id)
    def copy(self, default=None):
        default.update({'name':self.env['ir.sequence'].next_by_code('fleet.vehicle.contract.odometer')})
        return super(FleetVehicleContractOdometer,self).copy(default=default)

    @api.multi
    def compute_odometer_change(self):
        for km_contract in self:
            for line in km_contract.line_ids:
                data = {'vehicle_id':line.vehicle_id.id,'value':line.odometer_stop,'date':line.date_stop,'origin':'contract'}
                self.env['fleet.vehicle.odometer'].create(data)
        return True
    
    @api.multi
    def _check_date_stop(self) :
        for t in self:
            if t.date_stop < t.date_start:
                return False
        return True

    _constraints = [(_check_date_stop, "Erreur : 'Fin' doit être > 'Début' !", ['date_stop'])]
    
    @api.onchange('frequency')
    def onchange_frequency(self):
        lines = []
        contracts = self.env['fleet.vehicle.contract'].search([('auto_ok','=',True),('contract_cd','=',False),('km_frequency','=',self.frequency),('state','=','open')])
        for contract in contracts:
            lines.append((0,0,{
                               'contract_id':contract.id,
                               'vehicle_id' : contract.vehicle_id.id,
                               'odometer_start': contract.vehicle_id.odometer,
                               'odometer_stop' : contract.vehicle_id.odometer,
                               'date_start' : self.date_start,
                               'date_stop' : self.date_stop
                               }))
        self.line_ids = lines
        
class FleetVehicleContractOdometerLine(models.Model):
    _name='fleet.vehicle.contract.odometer.line'

    contract_id = fields.Many2one('fleet.vehicle.contract','Contrat',domain=[('state','=','open'),('contract_cd','=',False)])
    vehicle_id = fields.Many2one('fleet.vehicle',related='contract_id.vehicle_id',string='Véhicule',readonly=True)
    date_start = fields.Date('Date compteur début',required=True)
    date_stop = fields.Date('Date compteur fin',required=True)
    odometer_start = fields.Float('Compteur début',required=True)
    odometer_stop = fields.Float('Compteur fin',required=True)
    contract_odometer_id = fields.Many2one('fleet.vehicle.contract.odometer','Parent')

    @api.onchange('contract_id')
    def onchange_contract_id(self):
        self.vehicle_id = self.contract_id.vehicle_id.id
        self.odometer_start = self.contract_id.vehicle_id.odometer
        self.odometer_stop = self.contract_id.vehicle_id.odometer
        self.date_start = self.contract_odometer_id.date_start
        self.date_stop = self.contract_odometer_id.date_stop

    @api.onchange('vehicle_id')
    def onchange_vehicle_id(self):
        self.odometer_start = self.vehicle_id.odometer



    @api.multi    
    def _check_odometer(self) :
        for line in self:
            if line.odometer_stop <= line.odometer_start:
                return False
        return True
    
    @api.multi
    def _check_date_stop(self) :
        for line in self:
            if line.date_stop <= line.date_start:
                return False
        return True

    @api.multi
    def _check_line_date_start(self) :
        for line in self:
            if not (line.contract_odometer_id.date_start <= line.date_start <= line.contract_odometer_id.date_stop):
                return False
        return True
    
    @api.multi
    def _check_line_date_stop(self) :
        for line in self:
            if not (line.contract_odometer_id.date_start <= line.date_stop <= line.contract_odometer_id.date_stop):
                return False
        return True

    _constraints = [(_check_odometer, "Erreur : 'Compteur fin' doit être > 'Compteur début' !", ['odometer_stop']),
                    (_check_date_stop, "Erreur : 'Fin' doit être > 'Début' !", ['date_stop']),
                    (_check_line_date_start, "Erreur : la date de début n'est pas correcte !", ['date_start']),
                    (_check_line_date_stop, "Erreur : la date de début n'est pas correcte !", ['date_stop'])
                    ]



class FleetVehicleContractBail(models.Model):
    _name='fleet.vehicle.contract.bail'
    
    contract_id = fields.Many2one('fleet.vehicle.contract','Contrat')
    company_id = fields.Many2one('res.company',u'Société')
    agence_id = fields.Many2one('agence.agence','Agence')
    state = fields.Many2one('contract.bail.state',u'État')
    partner_id = fields.Many2one('res.partner','Client')
    amount = fields.Float('Montant')
    payment_mode_id = fields.Many2one('account.payment.mode',u'Règlement')
    notes = fields.Text('Commentaire')
    date = fields.Date(u'Date Opération')
    date_due = fields.Date("Expiration( Date limite )")
    validity_end = fields.Char("Fin validité( CB )")
    card = fields.Char("N°Carte")
    nature = fields.Many2one('contract.bail.nature','Nature')
    code = fields.Char('Code')

class ContractBailState(models.Model):
    _name='contract.bail.state'
    
    name = fields.Char(u'État',required=True)

class ContractBailNature(models.Model):
    _name='contract.bail.nature'
    
    name = fields.Char('Nature',required=True)


class FleetVehicleContractStop(models.Model):
    _name='fleet.vehicle.contract.stop'
    _description=u"Fiche de restitution"

    @api.one
    @api.depends("ret_end_odometer","ret_planned_odometer")
    def _compute_ret_ecart_km(self):
        self.ret_ecart_km = self.ret_end_odometer - self.ret_planned_odometer

    @api.one
    @api.depends("ret_date","expiration_date")
    def _compute_ret_ecart_date(self):
        ret_ecart_date = 0
        try:
            diff = fields.Date.from_string(self.expiration_date) - fields.Date.from_string(self.ret_date)
            ret_ecart_date = diff.days/30
        except:
            pass
        self.ret_ecart_date = ret_ecart_date


    @api.one
    @api.depends("contract_id","contract_id.amount_untaxed","contract_id.lld_nombre_mois")
    def _compute_amount_untaxed_sum(self):
        self.amount_untaxed_sum = self.contract_id.amount_untaxed * self.contract_id.lld_nombre_mois
        
    start_date = fields.Date(u'Date de départ')
    expiration_date = fields.Date(u'Date de retour prévue')
    ret_date = fields.Date(u'Date de retour')
    duree = fields.Integer(u"Durée prévue")
    ret_ecart_date = fields.Float(u"Nombre de mois restant",compute="_compute_ret_ecart_date",store=True)
    
    vehicle_odometer = fields.Float(u"Compteur départ")
    ret_planned_odometer = fields.Float(u"Compteur retour prévu")
    ret_end_odometer = fields.Float(u"Compteur retour")
    ret_ecart_km = fields.Float("Km supplémentaire",compute="_compute_ret_ecart_km",store=True)
    km_ecart = fields.Float(related="contract_id.km_ecart",string=u"Tolérance")
    km_sup_price_unit = fields.Float(u"Prix km sup")
    
    amount_total = fields.Monetary(related="contract_id.amount_total",string=u"Montant loyer",readonly=True)
    amount_untaxed_sum = fields.Monetary(u"Sommes loyers HT",compute="_compute_amount_untaxed_sum")
    
    ir_amount = fields.Monetary(u"Indemnités de restitution",readonly=True)
    currency_id  =fields.Many2one("res.currency",related="contract_id.currency_id",string=u"Devise",readonly=True)
    
    formula_id  =fields.Many2one("fleet.vehicle.contract.stop.config",string=u"Méthode de calcul")
    
    contract_id = fields.Many2one("fleet.vehicle.contract",u"Contrat",domain="[('contract_cd','=',False),('id','=',0)]",required=True)
    partner_id = fields.Many2one("res.partner",related="contract_id.partner_id",string=u"Client",domain="[('customer','=',True)]",readonly=True)
    driver_id = fields.Many2one("res.partner",related="contract_id.driver_id",string=u"Conducteur",domain="[('driver','=',True)]",readonly=True)
    address  =fields.Text(u"Adresse de restitution")
    vehicle_id = fields.Many2one("fleet.vehicle",related="contract_id.vehicle_id",sting=u"Parc",readonly=True)
    license_plate = fields.Char(related="vehicle_id.license_plate",string=u"Immatriculation",readonly=True)
    libelle = fields.Char(related="vehicle_id.libelle",string=u"Libellé",readonly=True)
    type_id = fields.Many2one("fleet.vehicle.type",related="vehicle_id.type_id",string=u"Libellé",readonly=True)
    
    sinister_ids = fields.One2many("fleet.vehicle.contract.stop.sinister","stop_id",u"Dégats")
    invoice_id = fields.Many2one("account.invoice",u"Ref. facture",readonly=True)
    
    @api.onchange("contract_id")
    def onchange_contract_id(self):
        self.start_date = self.contract_id.start_date
        self.expiration_date = self.contract_id.expiration_date
        self.duree = self.contract_id.lld_nombre_mois
        self.vehicle_odometer = self.contract_id.vehicle_odometer
        self.ret_planned_odometer = self.contract_id.planned_odometer + self.contract_id.vehicle_odometer
        self.ret_end_odometer = self.contract_id.ret_end_odometer
        self.km_sup_price_unit = self.contract_id.km_sup_price_unit
        

    @api.multi
    def action_ir_amount(self):
        formula = self.formula_id.formula
        context_eval = {
                        "amount_untaxed_sum":self.amount_untaxed_sum,
                        "ret_ecart_date" : self.ret_ecart_date,
                        "duree" : self.duree
                        }
        ir_amount = 0
        try:
            ir_amount = eval(formula,context_eval)
        except:
            pass
        self.ir_amount = ir_amount

    @api.multi
    def action_invoice_create(self):
        self.ensure_one()
        invoice_data = self.env["fleet.vehicle.contract"]._prepare_invoice_data(self.contract_id)
        invoice_data['invoice_line_ids'] = self._prepare_invoice_lines()
        invoice = self.env["account.invoice"].create(invoice_data)
        self.invoice_id = invoice.id
        return True

    @api.multi
    def _prepare_invoice_lines(self):
        self.ensure_one()
        invoice_lines = []
        product1 = self.env.ref("product.product_product10")
        product2 = self.env.ref("product.product_product11")
        product3 = self.env.ref("product.product_product5")
        amount_sinister = 0
        for line in self.sinister_ids:
            
            if not product1:
                continue
            amount_sinister += line.amount_total
        
        account_id1 = product1.property_account_income_id.id
        if not account_id1:
            account_id1 = product1.categ_id.property_account_income_categ_id.id
            
        account_id2 = product2.property_account_income_id.id
        if not account_id2:
            account_id2 = product2.categ_id.property_account_income_categ_id.id

        account_id3 = product3.property_account_income_id.id
        if not account_id3:
            account_id3 = product3.categ_id.property_account_income_categ_id.id
        
        contract = line.stop_id.contract_id
        if product1:
            invoice_lines.append((0, 0, {
                'name': product1.name,
                'account_id': account_id1,
                'price_unit': amount_sinister,
                'quantity': 1,
                'product_id': product1.id or False,
                'invoice_line_tax_ids': [(6, 0, product1.taxes_id.ids)],
                'contract_id' : contract.id,
                'vehicle_id' : contract.vehicle_id.id,
                'agence_id' : contract.agence_id.id,
            }))

        if product2:
            invoice_lines.append((0, 0, {
                'name': product2.name,
                'account_id': account_id2,
                'price_unit': self.ir_amount,
                'quantity': 1,
                'product_id': product2.id or False,
                'invoice_line_tax_ids': [(6, 0, product2.taxes_id.ids)],
                'contract_id' : contract.id,
                'vehicle_id' : contract.vehicle_id.id,
                'agence_id' : contract.agence_id.id,
            }))
        
        km_amount = self.ret_ecart_km*self.km_sup_price_unit if self.ret_ecart_km > self.km_ecart else 0
        if product3:
            invoice_lines.append((0, 0, {
                'name': product3.name,
                'account_id': account_id3,
                'price_unit': km_amount,
                'quantity': 1,
                'product_id': product3.id or False,
                'invoice_line_tax_ids': [(6, 0, product3.taxes_id.ids)],
                'contract_id' : contract.id,
                'vehicle_id' : contract.vehicle_id.id,
                'agence_id' : contract.agence_id.id,
            }))
        return invoice_lines

class FleetVehicleContractStopSinister(models.Model):
    _name='fleet.vehicle.contract.stop.sinister'
    
    @api.one
    @api.depends("amount","garantie")
    def _compute_amount_total(self):
        amount_total = self.amount
        if self.garantie:
            amount_total = 0
        self.amount_total = amount_total
        
    libelle_id = fields.Many2one("fleet.vehicle.contract.stop.sinisterlibelle",u"Libellé",required=True)
    amount  = fields.Float(u"Prix")
    garantie = fields.Boolean(u"Garantie")
    amount_total = fields.Float("Montant final",compute="_compute_amount_total",store=True)
    stop_id= fields.Many2one("fleet.vehicle.contract.stop","IR")

class FleetVehicleContractStopSinisterlibelle(models.Model):
    _name='fleet.vehicle.contract.stop.sinisterlibelle'
    
    name = fields.Char(u"Nom",required=True)
    
class FleetVehicleContractStopConfig(models.Model):
    _name='fleet.vehicle.contract.stop.config'
    
    name = fields.Char(u"Code",required=True)
    formula = fields.Char(u"Formule",default="amount_untaxed_sum*0.38*ret_ecart_date/(duree-4)")

