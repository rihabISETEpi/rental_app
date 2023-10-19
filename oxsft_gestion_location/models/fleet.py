# -*- coding: utf-8 -*-
import ast
from datetime import date, timedelta
import datetime
import logging
import time

# from fleet_vehicle_contract import CONTRACT_STATE ++zart
from odoo import api, fields, models,_, SUPERUSER_ID
from odoo.exceptions import UserError
from odoo.tools.misc import DEFAULT_SERVER_DATE_FORMAT, \
    DEFAULT_SERVER_DATETIME_FORMAT


_logger = logging.getLogger(__name__)

CONTRACT_STATE = [('waiting','En attente'),
                  ('devis', 'Devis'),
                  ('reservation', 'Réservation'),
                  ('open', 'Contrat'),
                  ('depart','Départ'),
                  ('closed', 'Clos')]

MAINTENANCE_TYPE_SELECTION1 = [
                               ('bm', 'Panne'),
                               ('cm', 'Corrective'),
                               ('pm', 'Programmée'),
                               ]


class FleetVehicle(models.Model):
    _inherit = "fleet.vehicle"

    @api.model
    def _vehicle_nature_get(self):
        nature_obj = self.env['fleet.vehicle.nature']

        result = []
        natures = nature_obj.search([])
        for nature in natures:
            result.append((nature.code, nature.name))
        return result

    @api.one
    @api.depends('last_move_id','last_move_id.name','move_ids','move_ids.vehicle_id',"move_ids.date_start",'move_ids.date_stop','move_ids.state')
    def _get_move_name(self):
        if self.last_move_id:
            self.last_move_name = self.last_move_id.name.name
        else:
            try:
                model,location_id = self.env['ir.model.data'].get_object_reference('fleet','fleet_vehicle_move_location0')
                location = self.env["fleet.vehicle.move.location"].browse(location_id)
                self.last_move_name = location.name
            except:
                self.last_move_name = "DISPONIBLE"


    custom_id = fields.Char('ID :')
    name = fields.Char(compute="_compute_vehicle_name", store=True)
    odometer = fields.Float(compute='_get_odometer', inverse='_set_odometer', string='Last Odometer', help='Odometer measure of the vehicle at the moment of this log')
    model_id =fields.Many2one('fleet.vehicle.model', 'Modèle :', help='Model of the vehicle', required=True)
    license_plate =fields.Char('Immatriculation :', required=False, help='License plate number of the vehicle (ie: plate number for a car)')
    alert_count = fields.Integer(compute="_compute_count_all2", string="Alertes")
    orders_count = fields.Integer(compute="_compute_count_all2",  string="Ordres")
    orders2_count = fields.Integer(compute="_compute_count_all2",  string="Assistances")
    vente_count = fields.Integer(compute="_compute_count_all2",  string="Ventes")
    achat_count = fields.Integer(compute="_compute_count_all2",  string="Achats")
    cmd_achat_count = fields.Integer(compute="_compute_count_all2",  string="Demande de prix")
    histo_count = fields.Integer(compute="_compute_count_all2",  string="Histo.")
    move_count = fields.Integer(compute="_compute_count_all2",  string="Mouvements.")
    contract_count2 = fields.Integer(compute="_compute_count_all2",  string='Contrats CD')
    contract_count_lld2 = fields.Integer(compute="_compute_count_all2",  string='Contrats LD')

    move_ids = fields.One2many('fleet.vehicle.move','vehicle_id','Mouvements')
    last_move_id = fields.Many2one("fleet.vehicle.move", compute='_get_last_move_id',string='Position actuelle :', domain="[('vehicle_id','=',active_id)]", store=True, help='Le dernier mouvement')
    last_move_name = fields.Char(compute="_get_move_name",string='Position actuelle :',help='Le dernier mouvement')
    product_id = fields.Many2one('product.product', 'Article :')
    libelle = fields.Char('Libellé :', size=256)
    lot = fields.Char('N° de série :')
        
    date = fields.Date('Du :')
    date_entree_prevue = fields.Date('Entrée prévue :')
    date_entree = fields.Date("Date d'entrée :")
    duree_prevue = fields.Float("Durée prévue :")
    sortie_prevue = fields.Date('Sortie prévue :')
    sortie_reelle = fields.Date('Sortie réelle :')
    last_odometer_date = fields.Datetime(compute="_get_last_odometer_date",string='Date dernière MAJ cpteur :')
    agence_id = fields.Many2one('agence.agence', "Agence")
    affectation_manuelle_id = fields.Many2one("fleet.vehicle.affectation_manuelle", "Affectation manuelle :")
    pool_vehicule_id = fields.Many2one("fleet.vehicle.pool", "Pool/non pool :")
    motif_de_sortie = fields.Char('Motif de la sortie :')
    type_id = fields.Many2one('fleet.vehicle.type', 'Type de matériel :')
        
    category_id = fields.Many2one('fleet.vehicle.category', 'Catégorie :')
    brand_id = fields.Many2one('fleet.vehicle.model.brand', string='Marque :')
    vehicle_id = fields.Many2one("fleet.vehicle", 'Véhicule accroché :',compute="_get_current_vehicle_id",store=True)
    
    nature_materiel = fields.Selection(_vehicle_nature_get, 'Nature du matériel :',default="vehicle_ok",change_default=True)
    
    vehicle_modification_ids = fields.One2many('fleet.vehicle.modification', 'vehicle_id', 'Affectation remorques', domain=[('state', '!=', 'unhooked')])
    trailer_modification_ids = fields.One2many('fleet.vehicle.modification', 'related_vehicle_id', 'Historique modifications', domain=[('state', '!=', 'unhooked')])
    owner = fields.Many2one('res.partner', 'Propriétaire :')
    manager = fields.Many2one('res.partner', 'Exploitant :')
        
    mouvement = fields.Boolean('Pris en compte dans les mouvements')
    planning = fields.Boolean('Présent dans le planning',default=True)

    #### Champs communs avec le modèle
    ss_type_id = fields.Many2one('fleet.vehicle.model.ss.type', 'SS type :')
    nature_cpt2 = fields.Many2one('fleet.vehicle.model.compteur', 'Nature du 2ième compteur :')
    nature_jauge = fields.Many2one('fleet.vehicle.model.jauge', 'Nature de la jauge :')
    capacite_reservoir =  fields.Float('Capacité réservoir :')
    capacite_reservoir2 = fields.Float('Capacité réservoir 2 :')
    cons_urbaine = fields.Float('Urbaine :')
    cons_mixte = fields.Float('Mixte 90 km/h :')
    cons_extra_urbaine =fields.Float('Extra urbaine 120 km/h :')

    t01 = fields.Char('Type mine (D.2.1) :')
    t03 = fields.Char('PTAC (F.2) :')
    t04 = fields.Char('Denom. Com. mine (D.3) :')
    t10 = fields.Many2one('fleet.vehicle.model.genre', 'Genre (J.1) :')
        
    t11 = fields.Char('Puissance fiscale (P.6) :')
    t13 = fields.Char('PTRA (F.3) :')
    t14 = fields.Char('Charge maxi tech (F.1) :')
    t20 = fields.Many2one('fleet.vehicle.model.carrosserie', 'Carrosserie (J.3) :')

    t21 = fields.Char('Puissance DIN (P.2) :')
    t23 = fields.Char('Charge utile :')
    t24 = fields.Char('Masse en service (G) :')
    t30 = fields.Many2one('fleet.vehicle.model.energie', 'Energie (P.3) :')

    t33 = fields.Char('PV (G.1) :')
    t34 = fields.Char('Catégorie (J) :')

    t42 = fields.Char('Nb places assises (S.1) :')
    t43 = fields.Char('Bruit (U.1) :')
    t44 = fields.Char('Carrosserie CE (J.2) :')

    t52 = fields.Char('Nb places debout (S.2) :')
    t53 = fields.Char('Régime moteur (U.2) :')
    t54 = fields.Char('CO2 (V.7) :')

    t62 = fields.Char('Nb portes :')
    t63 = fields.Char('Type variante (D.2) :')
    t64 = fields.Char('Classe env. (v.9) :')

    cylindre = fields.Char('Cylindrée (P.1) :')

        
    date_fabrication = fields.Date('Date de fabrication :')
    numero_carte_grise = fields.Char('N° carte grise :')
    code_peinture = fields.Char('Code peinture :')
    origin_country_id = fields.Many2one('res.country', "Pays d'origne :")
    moteur = fields.Char('N° moteur :')
        
    date_misc = fields.Date('Date 1ère MISC :')
    owner2 = fields.Many2one('res.partner', 'Propriétaire C.G. :')
    department_id = fields.Many2one('hr.department', 'Département :')
        
    # caractéristiques
        
    caracteristique_ids = fields.One2many('fleet.vehicle.model.caracteristique', 'vehicle_id', 'Caractéristiques')
    equipement_ids = fields.One2many('fleet.vehicle.model.equipement', 'vehicle_id', 'Équipements')
        
    vehicle_ids = fields.Many2many('fleet.vehicle', 'fleet_vehicle_fleet_vehicle_rel', 'vehicle_id1', 'vehicle_id2', string="Rattachement")
        
    # Achat
    fournisseur_id = fields.Many2one("res.partner", 'Fournisseur :')
    prix_catalogue = fields.Float('Prix catalogue :')
    numero_facture = fields.Char('Numéro de la facture :')
    date_facture = fields.Date('Date de facture :')
        
        
    prix_achat_ht = fields.Float("Prix d'achat HT :")
    montant_tva = fields.Float("Montant TVA :")
    montant_ttc = fields.Float(compute="_get_montant_ttc", string="Montant TTC :")

    prix_achat_ht_facture = fields.Float(compute="_get_amount_all", string="Prix d'achat HT :")
    montant_tva_facture = fields.Float(compute="_get_amount_all", string="Montant TVA :")
    montant_ttc_facture = fields.Float(compute="_get_amount_all", string="Montant TTC :")

    prix_achat_ht_cumul = fields.Float(compute="_get_amount_all", string="Prix d'achat HT :")
    montant_tva_cumul = fields.Float(compute="_get_amount_all", string="Montant TVA :")
    montant_ttc_cumul = fields.Float(compute="_get_amount_all", string="Montant TTC :")
        
    # Vente
    client_id = fields.Many2one('res.partner', 'Client')
    numero_facture_vente = fields.Char('Numéro de la facture :')
    date_facture_vente = fields.Date('Date de facture :')
        
    prix_vente_ht = fields.Float("Prix d'achat HT :")
    montant_tva_vente = fields.Float("Montant TVA :")
    montant_ttc_vente = fields.Float(compute="_get_montant_ttc_vente", string="Montant TTC :")

    prix_vente_ht_facture = fields.Float(compute="_get_amount_all_vente", string="Prix d'achat HT :")
    montant_tva_facture_vente = fields.Float(compute="_get_amount_all_vente", string="Montant TVA :")
    montant_ttc_facture_vente = fields.Float(compute="_get_amount_all_vente", string="Montant TTC :")

    prix_vente_ht_cumul = fields.Float(compute="_get_amount_all_vente", string="Prix d'achat HT :")
    montant_tva_cumul_vente = fields.Float(compute="_get_amount_all_vente", string="Montant TVA :")
    montant_ttc_cumul_vente = fields.Float(compute="_get_amount_all_vente", string="Montant TTC :")
        
    #historique
    operation_ids = fields.One2many('fleet.vehicle.operation.report', 'vehicle_id', 'Opérations')
        
    fr_quantity_total = fields.Float(compute="_get_data", string='Qté fournisseur :')
    clt_quantity_total = fields.Float(compute="_get_data", string='Qté client :')
    fr_ht_total = fields.Float(compute="_get_data", string='Total fournisseur :')
    clt_ht_total = fields.Float(compute="_get_data", string='Total client :')
    histo_solde = fields.Float(compute="_get_data", string='Solde :')
        
    garantie_state = fields.Selection([('expire', 'Expirée'), ('en_cours', 'En cours'), ('none', 'Aucune garantie')], 'Garantie',default="en_cours")

    @api.model_cr
    def init(self):
        try:
            rule = self.env.ref("fleet.fleet_rule_vehicle_visibility_user")
            rule.write({'active' :False})
        except:
            pass
        super(FleetVehicle,self).init()
        
    @api.multi
    def sale_clean(self):
        for vehicle in self:
            data = {
                    'numero_facture_vente' :'',
                    'date_facture_vente' :False,
                    'prix_vente_ht' :0,
                    'montant_tva_vente' :0,
                    }
            vehicle.write(data)
        return True

    @api.multi
    def purchase_clean(self):
        for vehicle in self:
            data = {
                    'numero_facture' :'',
                    'date_facture' :False,
                    'prix_achat_ht' :0,
                    'montant_tva' :0,
                    }
            vehicle.write(data)
        return True


    @api.depends('model_id', 'license_plate','lot')
    def _compute_vehicle_name(self):
        for record in self:
            name = ""
            #if record.model_id.brand_id.name:
             #   name = record.model_id.brand_id.name + '/'
            #name += record.model_id.name
            #if record.license_plate:
             #   name += ' / ' + record.license_plate
            
            if record.libelle :
                name = record.libelle
            else:
                name = record.model_id.name
            if record.license_plate:
                name = "[ " + record.license_plate + " ] " + name
            elif record.lot:
                name = "[ " + record.lot + " ] " + name
            record.name = name





    @api.one
    @api.depends('trailer_modification_ids.related_vehicle_id',
                 'vehicle_modification_ids.vehicle_id')
    def _get_current_vehicle_id(self):    
        """Récupère le véhicule courant accroché à la semi-remorque"""
        
        modification_ids = self.env['fleet.vehicle.modification'].search([('related_vehicle_id', '=', self.id), ('state', '=', 'hooked')])
        vehicle_id = False
        if modification_ids:
            vehicle_id = modification_ids[0].vehicle_id.id
        self.vehicle_id = vehicle_id

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        try:
            name = int(name)
            args2 = ['|','|','|',['id','=',name],['name',operator,name],['license_plate',operator,name],['lot',operator,name]]
        except:
            args2 = ['|','|',['name',operator,name],['license_plate',operator,name],['lot',operator,name]]
        
        args = args2+args
        
        recs = self.search(args, limit=limit)
        return recs.name_get()
    

    @api.multi
    def name_get(self):
        context = self.env.context
        if not context:
            return super(FleetVehicle,self).name_get()
        if context.get('display_all') or ('display_all' not in context):
            return super(FleetVehicle,self).name_get()
        
        start_date = context and context.get('start_date')
        expiration_date = context and context.get('expiration_date')
        if start_date:
            start_date = datetime.datetime.strptime(start_date, DEFAULT_SERVER_DATETIME_FORMAT).date()
        if expiration_date:
            expiration_date=datetime.datetime.strptime(expiration_date, DEFAULT_SERVER_DATETIME_FORMAT).date()
        
        vehicle_ids = self.get_vehicles_disponibilities(start_date,expiration_date)
        vehicles = self.browse(vehicle_ids)
        return super(FleetVehicle,vehicles).name_get()

    @api.multi
    def get_vehicles_disponibilities(self,date_start,date_end): 
        """Disponibilité du véhicule sur la base des location en cours"""
        """Retourne les identifiants des véhicules disponibles """
        
        
        context = self.env.context
        move_id = context and context.get('move_id') or False
        self._cr.execute("""select vehicle_id,id from fleet_vehicle_move where (date_start::date<=%s and date_stop::date>=%s)
                      or (date_start::date<=%s and date_stop::date>=%s)""",(date_start,date_start,date_end,date_end,))
        vehicle_ids= []
        used_vehicle_ids= []
        rqRes = self._cr.fetchall()
        for vehicle in rqRes:
            if move_id and (vehicle[1] == move_id):
                continue
            if vehicle[0] is not None:
                used_vehicle_ids.append(vehicle[0])
            
        all_vehicle_ids = []
        ordered_vehicle_ids= []
        ids = self.ids
        if ids:
            self._cr.execute("""select id,(select value from fleet_vehicle_odometer where 
                    vehicle_id=fv.id order by id desc limit 1) from fleet_vehicle fv where id in %s order by 
                    (select value from fleet_vehicle_odometer where 
                    vehicle_id=fv.id order by id desc limit 1) asc""",(tuple(ids),))
            rqRes = self._cr.fetchall()
            for vehicle in rqRes:
                if vehicle[1] is None:
                    all_vehicle_ids.append(vehicle[0])
                else:
                    ordered_vehicle_ids.append(vehicle[0])
            all_vehicle_ids.extend(ordered_vehicle_ids)
            
        for vehicle in self.browse(all_vehicle_ids):
            if vehicle.id not in used_vehicle_ids:
                vehicle_ids.append(vehicle.id)
        
        return vehicle_ids

    @api.one
    def is_used(self,date_start,date_end): 
        """Dire si un matériel donné est occupé selon l'interval spécifié"""
        """Retourne vrai ou faux """
        
        
        context = self.env.context
        ignored_move_ids = context and context.get('ignored_move_ids') or False
        self._cr.execute("""select id from fleet_vehicle_move where vehicle_id=%s and ( (date_start::date<=%s and date_stop::date>=%s)
                      or (date_start::date<=%s and date_stop::date>=%s) )""",(self.id,date_start,date_start,date_end,date_end,))
        rqRes = self._cr.fetchall()
        move_ids = []
        for move in rqRes:
            if ignored_move_ids and (move[0] in ignored_move_ids):
                continue
            if move[0] is not None:
                move_ids.append(move[0])
        
        return len(move_ids) > 0
    
    @api.onchange('category_id')
    def onchange_vehicle_category_id(self):
        if self.category_id:
            self.hook_ok = self.category_id.hook_ok
            self.nature_materiel = self.category_id.nature_materiel
    

    def _compute_count_all2(self):
        Alert = self.env['tms.gmao.pm']
        Order = self.env['mro.order']
        Purchase = self.env['purchase.order']
        Account = self.env['account.invoice']
        AccountInvoiceLine = self.env['account.invoice.line']
        Move = self.env['fleet.vehicle.move']
        Contract = self.env['fleet.vehicle.contract']
        for vehicle in self:
            vehicle_id = vehicle.id
            vehicle_ids = []
            vehicle_ids.append(vehicle_id)
            for rem in vehicle.vehicle_modification_ids:
                if rem.state == 'hooked':
                    vehicle_ids.append(rem.related_vehicle_id.id)
            taille12 = Alert.search_count([('vehicle_id', 'in', vehicle_ids), ('state', '!=', 'done')])
            taille2 = Order.search_count([('vehicle_id', 'in', vehicle_ids),('assistance','=',False)])
            taille22 = Order.search_count([('vehicle_id', 'in', vehicle_ids),('assistance','!=',False)])
            taille5 = Move.search_count([('vehicle_id', '=', vehicle_id)])
            taille6 = Contract.search_count([('vehicle_id', '=', vehicle_id),('contract_cd','!=',False)])
            taille7 = Contract.search_count([('vehicle_id', '=', vehicle_id),('contract_cd','=',False)])
            cmd_achat_count = Purchase.search_count([('vehicle_id', '=', vehicle_id),('state','in',('draft','sent','bid','cancel', 'confirmed'))])
            
            ###Count facture
            s_invoice_lines = AccountInvoiceLine.search([('product_id.vente', '=', True), ('vehicle_id', '=', vehicle.id),('invoice_id.type', 'in', ('out_invoice', 'in_refund')),('invoice_id.state','!=','cancel')])
            s_invoices = Account.search([('vehicle_id', '=', vehicle_id), ('type', '=', 'out_invoice'),('state','!=','cancel')])
            p_invoice_lines = AccountInvoiceLine.search([('product_id.achat', '=', True), ('vehicle_id', '=', vehicle.id),('invoice_id.type', 'in', ('in_invoice', 'out_refund')),('invoice_id.state','!=','cancel')])
            p_invoices = Account.search([('vehicle_id', '=', vehicle_id), ('type', '=', 'in_invoice'),('state','!=','cancel')])
            
            s_invoice_ids = s_invoices.ids
            p_invoice_ids = p_invoices.ids
            for line in s_invoice_lines:
                s_invoice_ids.append(line.invoice_id.id)
            for line in p_invoice_lines:
                p_invoice_ids.append(line.invoice_id.id)
            
            s_invoice_ids = set(s_invoice_ids)
            p_invoice_ids = set(p_invoice_ids)
            ###Count facture
            
            vehicle.alert_count = taille12
            vehicle.orders_count = taille2
            vehicle.orders2_count = taille22
            vehicle.vente_count = len(s_invoice_ids)
            vehicle.achat_count = len(p_invoice_ids)
            vehicle.cmd_achat_count = cmd_achat_count
            vehicle.move_count = taille5
            vehicle.contract_count2 = taille6
            vehicle.contract_count_lld2 = taille7


    @api.multi
    def _get_last_odometer_date(self):
        for vehicle in self:
            last_odometer_date = False
            odometer_id = self.env['fleet.vehicle.odometer'].search([('vehicle_id', '=', vehicle.id)], order="id desc", limit=1)
            if odometer_id:
                last_odometer_date = odometer_id[0].date
            vehicle.last_odometer_date = last_odometer_date
    
    @api.one
    @api.depends('prix_achat_ht','montant_tva')
    def _get_montant_ttc(self):
        self.montant_ttc = self.prix_achat_ht + self.montant_tva

    @api.one
    @api.depends('prix_vente_ht','montant_tva_vente')
    def _get_montant_ttc_vente(self):
        self.montant_ttc_vente = self.prix_vente_ht + self.montant_tva_vente

    @api.one
    @api.depends('prix_achat_ht','montant_tva','montant_ttc')
    def _get_amount_all(self):
        invoice_obj = self.env['account.invoice']
        invoice_line_obj = self.env['account.invoice.line']
        
        invoice_ids = invoice_obj.search([('vehicle_id', '=', self.id), ('type', 'in', ('in_invoice', 'out_refund')),('state','!=','cancel')])
        invoice_line_ids = invoice_line_obj.search([('product_id.achat', '=', True), ('invoice_id', 'in', invoice_ids.ids)])
        invoice_line_ids = invoice_line_ids.ids
        invoice_line_ids.extend(invoice_line_obj.search([('product_id.achat', '=', True), ('vehicle_id', '=', self.id),('invoice_id.type', 'in', ('in_invoice', 'out_refund')),('invoice_id.state','!=','cancel')]).ids)
        invoice_line_ids = set(invoice_line_ids)
        val1 = val2 = val3 = 0.0
        for invoice_line in invoice_line_obj.browse(invoice_line_ids):
            invoice = invoice_line.invoice_id
            price = invoice_line.price_unit * (1 - (invoice_line.discount or 0.0) / 100.0)
            taxes = invoice_line.invoice_line_tax_ids.compute_all(price,currency=invoice_line.invoice_id.currency_id,
                                                                  quantity=invoice_line.quantity, product=invoice_line.product_id, partner=invoice.partner_id)['taxes']
            
            amount_tax = 0
            for tax in taxes:
                amount_tax += tax['amount']
            cur = invoice_line.invoice_id.currency_id
            val1 += cur.round(invoice_line.price_subtotal)
            val2 += cur.round(amount_tax)
            val3 += cur.round(invoice_line.price_subtotal + amount_tax)

        self.prix_achat_ht_facture = val1
        self.montant_tva_facture = val2
        self.montant_ttc_facture = val3
            
        self.prix_achat_ht_cumul = val1 + self.prix_achat_ht
        self.montant_tva_cumul = val2 + self.montant_tva
        self.montant_ttc_cumul = val3 + self.montant_ttc
        
    @api.one
    @api.depends('prix_vente_ht','montant_tva_vente','montant_ttc_vente')
    def _get_amount_all_vente(self):
        invoice_obj = self.env['account.invoice']
        invoice_line_obj = self.env['account.invoice.line']
        invoice_ids = invoice_obj.search([('vehicle_id', '=', self.id), ('type', 'in', ('out_invoice', 'in_refund')),('state','!=','cancel')])
        invoice_line_ids = invoice_line_obj.search([('product_id.vente', '=', True), ('invoice_id', 'in', invoice_ids.ids)])
        invoice_line_ids = invoice_line_ids.ids
        invoice_line_ids.extend(invoice_line_obj.search([('product_id.vente', '=', True), ('vehicle_id', '=', self.id),('invoice_id.type', 'in', ('out_invoice', 'in_refund')),('invoice_id.state','!=','cancel')]).ids)
        invoice_line_ids = set(invoice_line_ids)
        val1 = val2 = val3 = 0.0
        for invoice_line in invoice_line_obj.browse(invoice_line_ids):
            invoice = invoice_line.invoice_id  
            price = invoice_line.price_unit * (1 - (invoice_line.discount or 0.0) / 100.0)
            taxes = invoice_line.invoice_line_tax_ids.compute_all(price,currency=invoice_line.invoice_id.currency_id,
                                                                  quantity=invoice_line.quantity, product=invoice_line.product_id, partner=invoice.partner_id)['taxes']
            
            amount_tax = 0
            for tax in taxes:
                amount_tax += tax['amount']
            cur = invoice_line.invoice_id.currency_id
            val1 += cur.round(invoice_line.price_subtotal)
            val2 += cur.round(amount_tax)
            val3 += cur.round(invoice_line.price_subtotal + amount_tax)

        self.prix_vente_ht_facture = val1
        self.montant_tva_facture_vente = val2
        self.montant_ttc_facture_vente = val3
            
        self.prix_vente_ht_cumul = val1 + self.prix_vente_ht
        self.montant_tva_cumul_vente = val2 + self.montant_tva_vente
        self.montant_ttc_cumul_vente = val3 + self.montant_ttc_vente


    @api.one
    @api.depends('operation_ids.fr_quantity','operation_ids.clt_quantity',
                 'operation_ids.fr_ht','operation_ids.clt_ht')
    def _get_data(self):
        val1 = val2 = val3 = val4 =  0
        for line in self.operation_ids:
            if line.exclure:
                continue
            val1 += line.fr_quantity
            val2 += line.clt_quantity
            val3 += line.fr_ht
            val4 += line.clt_ht
                
                
        self.fr_quantity_total = val1
        self.clt_quantity_total  = val2
        self.fr_ht_total = val3
        self.clt_ht_total  = val4
        self.histo_solde = val4 - val3

    @api.onchange('date_entree_prevue', 'duree_prevue')
    def onchange_params(self):
        if self.date_entree_prevue:
            interval = timedelta(days=self.duree_prevue)
            self.sortie_prevue = datetime.datetime.strptime(self.date_entree_prevue, DEFAULT_SERVER_DATE_FORMAT).date() + interval

    def _get_odometer(self):
        FleetVehicalOdometer = self.env['fleet.vehicle.odometer']
        for record in self:
            vehicle_odometer = FleetVehicalOdometer.search([('vehicle_id', '=', record.id)], limit=1, order='id desc')
            if vehicle_odometer:
                record.odometer = vehicle_odometer.value
            else:
                record.odometer = 0

    def _set_odometer(self):
        for record in self:
            if record.odometer:
                date = fields.Date.context_today(record)
                data = {'value': record.odometer, 'date': date, 'vehicle_id': record.id}
                self.env['fleet.vehicle.odometer'].create(data)

    
    @api.depends('move_ids','move_ids.vehicle_id',"move_ids.date_start",'move_ids.date_stop','move_ids.state')
    def _get_last_move_id(self):
        FleetVehicleMove = self.env['fleet.vehicle.move']
        for vehicle in self:
            datetime_str = fields.Datetime.now()
            ### RECHERCHER LE MOUVEMENT ACTIF À LA DATE ACTUELLE.CETTE RECHERCHE DOIT RETOURNER AU MAXIMUM 1 UNE LIGNE
            moves = FleetVehicleMove.search([('vehicle_id', '=', vehicle.id),('date_start', '<=', datetime_str),('date_stop','>=',datetime_str)], limit=1, order='date_start desc')
            if moves:
                vehicle.last_move_id = moves[0].id
            else:
                ### SINON RECHERCHER LE MOUVEMENT DISPONIBLE
                dispo_moves = False
                other_moves = False
                try:
                    dispo_loc = self.env.ref('fleet.fleet_vehicle_move_location0')
                    dispo_moves = FleetVehicleMove.search([('vehicle_id', '=', vehicle.id),('name', '=', dispo_loc.id)],order="date_start desc")
                    other_moves = FleetVehicleMove.search([('vehicle_id', '=', vehicle.id),('name', '!=', dispo_loc.id)])
                except:
                    pass
                if dispo_moves:
                    vehicle.last_move_id = dispo_moves[0].id
                elif not other_moves:###SI AUCUN MOUVEMENT DE DISPONIBILITÉ TROUVÉ , ON CRÉE LE MOUVEMENT DE DISPONIBILITÉ
                    move = self.create_move(vehicle)
                    vehicle.last_move_id = move.id
            



    _sql_constraints = [
        ('custom_id_uniq', 'unique(custom_id)', "L'ID doit être unique!"),
    ]
    
    def create_pm_and_link(self, model_ids):
        for model in self.env['fleet.vehicle.model'].browse(model_ids):
            vehicles = self.search([('model_id', '=', model.id)])
            for vehicle in vehicles:
                alerte_ids = []
                dictionnaire = {}   ### DICTIONNAIRE CONTIENT COMME CLÉ LE MODÈLE D'ENTRETIEN QUI SUR LE MODÈLE DE VÉHICLE ET COMME VALEUR L'ALERTE QUI A ÉTÉ CRÉÉE SUR LA BASE DE CE MODÈLE D'ENTRETIEN
                for alert in model.pmm_ids:
                    filtre_lines = []
                    if alert.service_type_id.code != 'ctrlapol':
                        for filtre_line in alert.line_ids:
                            filtre_lines.append((0, 0, {'product_id':filtre_line.product_id.id, 'product_qty':filtre_line.product_qty}))
                        alert_data = {
                              'vehicle_id' : vehicle.id,
                              'service_type_id' : alert.service_type_id.id,
                              'meter' :alert.meter,
                              'periodic' :alert.periodic,
                              'first_interval' : alert.first_interval,
                              'interval' : alert.interval,
                              'warn_period' : alert.warning if alert.meter != 'km' else 0,
                              'days_last_done' :  vehicle.date_misc if vehicle.date_misc else date.today() ,
                              'km_last_done' : vehicle.odometer,
                              'meter_ecart0' : alert.meter_ecart0,
                              'meter_ecart' : alert.meter_ecart,
                              'valeur_ecart' : alert.valeur_ecart,
                              'description': alert.name,
                              'pm_model_id' : alert.id,
                              'model_template_id' : alert.model_template_id.id,
                              'line_ids' : filtre_lines,
                            }
                        prev_alerts = self.env['tms.gmao.pm'].search([('vehicle_id', '=', vehicle.id), ('pm_model_id', '=', alert.id)])
                        if prev_alerts:  # #NE PAS CRÉER DE MAINTENANCE PRÉVENTIVE CAR DEJA CRÉÉE
                            alert_new = prev_alerts[0]
                            alert_id = alert_new.id
                            product_lines = self.env['fleet.line.reparation'].search([('pm_id', '=', alert_id)])
                            product_lines.unlink()
                            alert_new.write(alert_data)
                        else:
                            alert_new = self.env['tms.gmao.pm'].create(alert_data)
                            alert_new.generate_alert()
                            alert_id = alert_new.id
                        if alert.pm_model_id.id:
                            dictionnaire[alert.pm_model_id.id] = alert_id
                        alerte_ids.append(alert_id)
                for alert in model.pmm_ids: ###l'ORDRE DE CRÉATION EST IMPORTANTE.Au MOMENT DE ;A CRÉATION DU CONTROLE ANTI POLUTION , LE CONTROLE TECHNIQUE S'IL Y A DOIT AVOIR DÉJÀ ÉTÉ CRÉER
                    filtre_lines = []
                    # ##SI CONTROLE ANTI-POLLUTION , NE PAS DECLENCHER L'ALERTE CAR ATTENTE DE LE FIN DU CONTROLE TECHINIQUE
                    if alert.service_type_id.code == 'ctrlapol':
                        tech_alert = self.env['tms.gmao.pm'].search([('vehicle_id', '=', vehicle.id), ('service_type_id.code', '=', 'ctrltech')], limit=1)
                        for filtre_line in alert.line_ids:
                            filtre_lines.append((0, 0, {'product_id':filtre_line.product_id.id, 'product_qty':filtre_line.product_qty}))
                        alert_data = {
                                'vehicle_id' : vehicle.id,
                                'service_type_id' : alert.service_type_id.id,
                                'meter' :alert.meter,
                                'periodic' :alert.periodic,
                                'first_interval' : alert.first_interval,
                                'interval' : alert.interval,
                                'warn_period' : alert.warning if alert.meter != 'km' else 0,
                                'days_last_done' :  tech_alert.days_next_due,
                                'km_last_done' : tech_alert.km_next_due,
                                'meter_ecart0' : alert.meter_ecart0,
                                'meter_ecart' : alert.meter_ecart,
                                'valeur_ecart' : alert.valeur_ecart,
                                'description': alert.name,
                                'pm_model_id' : alert.id,
                                'model_template_id' : alert.model_template_id.id,
                                'line_ids' : filtre_lines,
                                }
                        
                        prev_alerts = self.env['tms.gmao.pm'].search([('vehicle_id', '=', vehicle.id), ('pm_model_id', '=', alert.id)])
                        if prev_alerts:  # #NE PAS CRÉER DE MAINTENANCE PRÉVENTIVE DEJA EXISTANTE
                            alert_new = prev_alerts[0]
                            alert_id = alert_new.id
                            product_lines = self.env['fleet.line.reparation'].search([('pm_id', '=', alert_id)])
                            product_lines.unlink()
                            alert_new.write(alert_data)
                        else:
                            alert_id = self.env['tms.gmao.pm'].create(alert_data).id
                        if alert.pm_model_id.id:
                            dictionnaire[alert.pm_model_id.id] = alert_id
                        alerte_ids.append(alert_id)
        
                # #TRAITEMENT DES ALERTES LIÉES
                for key, value in dictionnaire.items():
                    for a in self.env['tms.gmao.pm'].browse(alerte_ids):
                        if a.pm_model_id.id == key:
                            self.env['tms.gmao.pm'].get_2pm_linked(a.id, value)
                            
        return True

    def create_move(self,vehicle):
        ###DÉBUT RENDRE LE MATÉRIEL DISPONIBLE
        ###CRÉER UN MOUVEMENT POUR QUE LE MATÉRIEL APPARAISSE DANS LE PLANNING
        data_id = False
        move = self.env["fleet.vehicle.move"]
        try:
            model, data_id = self.env['ir.model.data'].get_object_reference('fleet', 'fleet_vehicle_move_location0')
        except:
            pass
        if data_id:
            ddate = fields.Datetime.now()
            data = {"name" :data_id, 'date_start':ddate,'date_stop':ddate, 'vehicle_id':vehicle.id,'src_agence_id':vehicle.agence_id.id,'dest_agence_id':vehicle.agence_id.id}
            move= self.env['fleet.vehicle.move'].create(data)
        else:
            print('Erreur emplacement destination.')
            #raise UserError(_(u'Erreur emplacement arrivé.'))
        ###FIN RENDRE LE MATÉRIEL DISPONIBLE
        return move
        
    @api.model
    @api.returns('self', lambda value:value.id)
    def create(self, vals):
        vehicle = super(FleetVehicle, self).create(vals)
        self.create_pm_and_link(vals.get('model_id'))
        self.create_move(vehicle)
        return vehicle

    @api.multi
    def return_action_to_open(self):
        """ This opens the xml view specified in xml_id for the current vehicle """
        self.ensure_one()
        vehicle_ids = []
        xml_id = self.env.context.get('xml_id')
        if xml_id:
            res = self.env['ir.actions.act_window'].for_xml_id('fleet', xml_id)
            ctx = {}
            domain = []
            if res.get('context'):
                ctx = ast.literal_eval(res['context'])
            if res.get('domain'):
                domain = ast.literal_eval(res.get('domain'))
            ctx.update({'default_vehicle_id': self.id})
            domain.extend([('vehicle_id', '=', self.id)])

            res.update(
                context=ctx,
                domain=domain
            )
            if xml_id in ['action_fleet_vehicle_filtre', 'action_orders','action_orders2', 'action_tms_gmao_pm_alert']:
                vehicle = self
                vehicle_ids.append(vehicle.id)
                for rem in vehicle.vehicle_modification_ids:
                    if rem.state == 'hooked':
                        vehicle_ids.append(rem.related_vehicle_id.id)
                domain = [('vehicle_id', 'in', vehicle_ids)]
                if xml_id == "action_tms_gmao_pm_alert":
                    domain.append(('state', '!=', 'done'))
                if xml_id == "action_orders":
                    domain.append(('assistance', '=', False))
                if xml_id == "action_orders2":
                    domain.append(('assistance', '!=', False))
                res.update(domain=domain)
            return res
        return False


    @api.multi
    def return_action_to_open2(self):
        """ This opens the xml view specified in xml_id for the current vehicle """
        self.ensure_one()
        xml_id = self.env.context.get('xml_id')
        module = self.env.context.get('module') or 'fleet'
        if xml_id:
            res = self.env['ir.actions.act_window'].for_xml_id(module, xml_id)
            ctx = ast.literal_eval(res.get('context'))
            ctx.update({'default_vehicle_id': self.id})
            domain = ast.literal_eval(res.get('domain'))
            domain.append(('vehicle_id', '=', self.id))
            res.update(
                context=ctx,
                domain=domain
            )
            return res
        return False


    @api.onchange('model_id')
    def _onchange_model(self):
        super(FleetVehicle,self)._onchange_model()
        
        model_read = self.model_id.read()
        data = {}
        if len(model_read) > 0:
            data = model_read[0]
        data['create_uid'] = False
        data['write_uid'] = False
        data['libelle'] = data.get('name')
        return {
            'value':data
        }
    

class FleetServiceType(models.Model):
    _inherit = 'fleet.service.type'

    code = fields.Char('Code')
    mro_ok = fields.Boolean('MRO')
    maintenance_type = fields.Selection(MAINTENANCE_TYPE_SELECTION1, 'Type de maintenance')



class FleetVehicleOdometer(models.Model):
    _inherit = 'fleet.vehicle.odometer'

    unit = fields.Selection([('kilometers', 'kilomètres'), ('miles', 'Miles')],related='vehicle_id.odometer_unit', string="Unit", readonly=True)
    date = fields.Datetime('Date',default=fields.Datetime.now)
    origin = fields.Selection([('odometer', 'Relevé'), ('fuel', 'Carburant'), ('mro', 'Ordre de maintenance'), ('alerte', 'Alerte'),('contract','Contrat')], 'Origine')


    @api.model
    @api.returns('self', lambda value:value.id)
    def create(self, vals):
        context = self.env.context
        if context and not vals.get('origin'):
            if context.get('xml_id') == 'fleet_vehicle_log_fuel_act':
                vals['origin'] = 'fuel'
            else:
                vals['origin'] = 'odometer'
        return super(FleetVehicleOdometer, self).create(vals)


class FleetVehicleNature(models.Model):
    _name = "fleet.vehicle.nature"
    
    code = fields.Char('Code',required=True)
    name = fields.Char('Nom',required=True)


    _sql_constraints = [
                        ('code_uniq', 'unique(code)', "Le code doit être unique")
                        ]
    
class FleetVehicleModification(models.Model):
    """Modification du parc (accrochage/décrochage véhicule - semi-remorque)"""
    _name = 'fleet.vehicle.modification'
    _description = 'Modification camion'

    @api.model
    @api.returns('self', lambda value:value.id)
    def create(self, vals):
        if ('name' not in vals) or (vals.get('name') == '/'):
            vals['name'] = self.env['ir.sequence'].next_by_code('fleet.vehicle.modification')
        mod_id = super(FleetVehicleModification, self).create(vals)
        self.set_hook([mod_id])
        return mod_id

    @api.multi
    @api.returns('self', lambda value:value.id)
    def copy(self, default=None):
        if default is None:
            default = {}
        default = default.copy()
        default['name'] = self.env['ir.sequence'].next_by_code('fleet.vehicle.modification')
        default['state'] = 'progress'
        return models.Model.copy(self, default=default)


    @api.multi
    def unlink(self):
        for modification in self:
            if modification.state != 'progress':
                #raise UserError(_("Vous ne pouvez pas supprimer une modification déjà traitée."))
                raise UserError(_('Vous ne pouvez pas supprimer une modification déjà traitée.'))
        return super(FleetVehicleModification, self).unlink()
    
    @api.multi
    def set_unhook(self):
        """Décrochage"""
        for modification in self:
            if modification.state == 'hooked' :
                date_unhook = False
                if modification.date_unhook:
                    date_unhook = modification.date_unhook
                else:
                    date_unhook = time.strftime('%Y-%m-%d %H:%M:%S')
                modification.write({'state':'unhooked', 'date_unhook': date_unhook})
        return True

    
    def is_trailer_hooked(self,related_vehicle_id):
        """Teste si la remorque est accrochée"""
        modification_ids = self.search([('related_vehicle_id', '=', related_vehicle_id), ('state', '=', 'hooked')])
        if len(modification_ids) > 0:
            return modification_ids
        return False
   
    
    def is_vehicle_hooked(self,vehicle_id, nature_materiel):
        """Teste si le véhicule est accroché"""
        modification_ids = self.search([('vehicle_id', '=', vehicle_id), ('nature_materiel', '=', nature_materiel), ('state', '=', 'hooked')])
        if len(modification_ids) > 0:
            return modification_ids
        return False
    
    @api.multi
    def set_hook(self):
        """Accrochage"""
        for modification in self:
            date_hook = False
            if modification.date_hook:
                date_hook = modification.date_hook
            else:
                date_hook = time.strftime('%Y-%m-%d %H:%M:%S')
            modification.write({'state':'hooked', 'date_hook': date_hook})
        return True

    @api.onchange('vehicle_id')
    def onchange_vehicle_id(self):
        """évènement lors du changement du véhicule"""
        
        self.vehicle_code = self.vehicle_id.license_plate

    @api.model
    def _vehicle_nature_get(self):
        nature_obj = self.env['fleet.vehicle.nature']

        result = []
        natures = nature_obj.search([])
        for nature in natures:
            result.append((nature.code, nature.name))
        return result

    name = fields.Char('Référence', required=True, readonly=True,default="/")
    vehicle_id = fields.Many2one('fleet.vehicle', 'Véhicule', states={'progress': [('readonly', False)]})
    vehicle_code = fields.Char('Immatriculation', size=50)
    date_hook = fields.Datetime('Date de début', help="Date d'accrochage")
    date_unhook = fields.Datetime('Date de fin', help="Date de décrochage")
    nature_materiel = fields.Selection(_vehicle_nature_get, 'Type de rattachement',default="vehicle_ok",change_default=True)
    related_vehicle_id = fields.Many2one('fleet.vehicle', 'Matériel rattaché', states={'progress': [('readonly', False)]})
    state = fields.Selection([('unhooked', 'Décroché'), ('hooked', 'Accroché'), ('progress', 'En cours')], 'Statut', readonly=True,default="progress")


    _sql_constraints = [
                        ('name_uniq', 'unique(name)', "Le nom d'une modification doit être unique")
                        ]

class FleetVehicleAffectationManuelle(models.Model):
    _name = "fleet.vehicle.affectation_manuelle"

    name = fields.Char('Nom')

    
class FleetVehiclePool(models.Model):
    _name = "fleet.vehicle.pool"
    
    name = fields.Char('Nom')


class FleetVehicleOperationNature(models.Model):
    _name = "fleet.vehicle.operation.nature"

    code = fields.Char('Code')
    name = fields.Char('Libellé', required=True)

    

class FleetVehicleMoveLocation(models.Model):
    _name = "fleet.vehicle.move.location"
    
    code = fields.Char('Code', required=True)
    name = fields.Char("Libellé", required=True)


class FleetVehicleMoveEvent(models.Model):
    _name = "fleet.vehicle.move.event"

    name = fields.Char('Nom',required=True)
    

class FleetVehicleMoveMotif(models.Model):
    _name = "fleet.vehicle.move.motif"

    name = fields.Text('Description',required=True)

class FleetVehicleMoveMainstate(models.Model):
    _name = "fleet.vehicle.move.mainstate"

    name = fields.Char('Nom',required=True)

class FleetVehicleMoveType(models.Model):
    _name = "fleet.vehicle.move.type"

    code = fields.Char('Code',required=True)
    name = fields.Char('Nom',required=True)
    color = fields.Char('Couleur')
    textcolor = fields.Char('Couleur du text')


class FleetVehicleMove(models.Model):
    _name = "fleet.vehicle.move"

    @api.model
    def _cron_remove_unsed_dispo(self):
        dispo_loc = self.env.ref('fleet.fleet_vehicle_move_location0')
        for vehicle in self.env['fleet.vehicle'].search([]):
            move = vehicle.last_move_id
            other_moves =self.search([('vehicle_id','=',vehicle.id),('name','!=',dispo_loc.id)]).ids
            dispo_moves =self.search([('vehicle_id','=',vehicle.id),('name','=',dispo_loc.id)],order="date_start desc,id desc")
            if other_moves:
                print("---REMOVE MOVE",dispo_moves)
                dispo_moves.unlink()
            elif dispo_moves: 
                if move.name.id == dispo_loc.id:
                    rem_dispo_moves = dispo_moves - move
                    print("---REMOVE MOVE",rem_dispo_moves)
                    rem_dispo_moves.unlink()
                else:
                    rem_dispo_moves = dispo_moves - dispo_moves[0]
                    print("---REMOVE MOVE",rem_dispo_moves)
                    rem_dispo_moves.unlink()
        return True

    """
    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        dispo_loc = self.env.ref('fleet.fleet_vehicle_move_location0')
        for vehicle in self.env['fleet.vehicle'].search([]):
            move = vehicle.last_move_id
            other_moves =self.search([('vehicle_id','=',vehicle.id),('name','!=',dispo_loc.id)]).ids
            dispo_moves =self.search([('vehicle_id','=',vehicle.id),('name','=',dispo_loc.id)],order="date_start desc,id desc")
            if other_moves:
                dispo_moves.unlink()
            elif dispo_moves: 
                if move.name.id == dispo_loc.id:
                    rem_dispo_moves = dispo_moves - move
                    rem_dispo_moves.unlink()
                else:
                    rem_dispo_moves = dispo_moves - dispo_moves[0]
                    rem_dispo_moves.unlink()
        return models.Model.search_read(self, domain=domain, fields=fields, offset=offset, limit=limit, order=order)
    """
    @api.model
    def _get_default_company(self):
        return self.env.user.company_id.id
    
    @api.model
    def _get_src_agence_id(self):
        return self.env.user.agence_id.id

    @api.model
    def _get_dest_agence_id(self):
        return self.env.user.agence_id.id

    @api.one
    @api.depends('date_start','date_stop')
    def _get_duration(self):
        duration = ""
        if self.date_stop:
            date_start = fields.Datetime.from_string(self.date_start)
            date_stop = fields.Datetime.from_string(self.date_stop)
            diff = date_stop - date_start
            duration = str(int(diff.total_seconds() / 3600)) + " Heure(s)"
        self.duration  =duration

    @api.one
    @api.depends('odometer_end','odometer_start')
    def _get_diff_odometer(self):
        diff = self.odometer_end - self.odometer_start
        if diff < 0:
            diff = 0
        self.diff_odometer = diff

    @api.multi
    def create_link(self ,prev_move , move ):
        if not prev_move:
            return False
        try:
            prev_move.fr_to_cible_id = move.id
            move.source_id = prev_move.id
        except:
            return False
        return True

    @api.one
    def _get_late_value(self):
        late = False
        contract = self.contract_id
        if contract:
            if contract.state not in ('devis','reservation') and contract.expiration_date < fields.Datetime.now() and not contract.return_ok:
                late = True
        self.late = late
    
    @api.one
    def _get_dispo_move(self):
        dispo_loc = self.env.ref('fleet.fleet_vehicle_move_location0')
        dispo_move = False
        if self.name.id == dispo_loc.id:
            dispo_move = True
        self.dispo_move = dispo_move
    
    code = fields.Char('N° Mouvement :', readonly=True,default="/")
    model_id = fields.Many2one('fleet.vehicle.model',related='vehicle_id.model_id', string='Modèle :',store=True, readonly=True)
    category_id = fields.Many2one('fleet.vehicle.category',related='vehicle_id.category_id', string='Catégorie :', store=True, readonly=True)
    fuel_qty_start = fields.Integer('Carburant départ :')
    fuel_qty_end = fields.  Integer('Carburant retour :')
    license_plate = fields.Char(related='vehicle_id.license_plate', string='Immat. :', readonly=True, store=True)
    lot = fields.Char(related='vehicle_id.lot', string='N° Série :', readonly=True, store=True)
    vehicle_id = fields.Many2one('fleet.vehicle', 'Véhicule :', required=True)
    source_id = fields.Many2one('fleet.vehicle.move', 'Pos. départ :')
    name = fields.Many2one('fleet.vehicle.move.location', 'Position :', required=True)
    fr_to_cible_id = fields.Many2one('fleet.vehicle.move', 'Pos. arrivée :')
              
    src_agence_id = fields.Many2one('agence.agence','Age départ :',default=_get_src_agence_id)
    dest_agence_id = fields.Many2one('agence.agence','Age arrivée :',default=_get_dest_agence_id)
    odometer_start = fields.Float('Cpteur départ :')
    odometer_end = fields.Float('Cpteur arrivée :')
    odometer_start2 = fields.Float('Cpteur2 départ :')
    odometer_end2 = fields.Float('Cpteur2 arrivée :')
    diff_odometer = fields.Float(compute="_get_diff_odometer", string='Parcourus :')
    close = fields.Boolean('Mvt clos')
              
    date_start = fields.Datetime('Date de départ :', required=True)
    date_stop = fields.Datetime('Date de retour :',required=True)
    #duration = fields.Float(compute="_get_duration", string='Durée :')
    partner_id = fields.Many2one('res.partner', 'Client :')
    driver_id = fields.Many2one('res.partner', 'Conducteur :')
    driver_address = fields.Text('Adresse :')
    partner_address = fields.Text('Adresse :')
    contract_id = fields.Many2one('fleet.vehicle.contract', 'Contrat :',domain=[('state','in',('reservation','open'))])
    contract_state = fields.Selection(CONTRACT_STATE,related='contract_id.state',string="Statut du contrat")
    contract_cd = fields.Boolean(related='contract_id.contract_cd',string="Contrat CD")
    doc_type_id = fields.Many2one('fleet.vehicle.move.type', 'Type de document :')
    color = fields.Char(related='doc_type_id.color',string='Couleur (P)')
    textcolor = fields.Char(related='doc_type_id.textcolor',string='Couleur du text (P)')

    mro_id = fields.Many2one('mro.order', 'Maintenance(OR)')
    user_id = fields.Many2one('res.users', 'Créateur du mouvement :',default=lambda self:self._uid)
    state = fields.Selection([('draft', 'En cours'), ('done', 'Terminé')], 'Statut',default="draft")
              
    event_id = fields.Many2one('fleet.vehicle.move.event','Évènement :')
    acriss = fields.Char('Code ACRISS :')
              
    ##ONGLET DIVERS
    d_motif_id = fields.Many2one('fleet.vehicle.move.motif','Motif :')
    d_niveau = fields.Char('Niveau :')
    d_doc_num = fields.Char('N° de document :')
    d_main_state_id = fields.Many2one('fleet.vehicle.move.mainstate',"État d'entretien :")
    d_prev_panne = fields.Char('Prév. de panne (h) :')
    product_id = fields.Many2one('product.product','Produit :')
    default_code = fields.Char('Immat. :')
    uom_id = fields.Many2one('product.uom','Unité :')
    d_category_id = fields.Many2one('fleet.vehicle.category','Catégorie :')
    d_libelle = fields.Char('Libellé matériel :')
    d_model_id = fields.Many2one('fleet.vehicle.model','Modèle :')
    d_origin = fields.Char('Maj Origine :')
    d_ref = fields.Char('Référence :')
    company_id = fields.Many2one('res.company','Société :',default=_get_default_company)
    d_date_invoice_start = fields.Datetime('Début de fac. :')
    d_date_invoice_stop = fields.Datetime('Fin de fac. :')
    d_date_invoice_last = fields.Datetime('Dern. période fac. :')
    d_qty = fields.Float('Qt. facturée :')
    d_date_archive = fields.Date("Date d'archivage :")
              
    ##ONGLET DÉPART ET POSITIONNEMENT
    dp_src_partner_id = fields.Many2one('res.partner','Tiers')
    dp_src_address = fields.Text('Adresse')
    dp_dest_partner_id = fields.Many2one('res.partner','Tiers')
    dp_dest_address = fields.Text('Adresse')
    
    
    parent_id = fields.Many2one("fleet.vehicle.move",'Parent')

    late = fields.Boolean(compute="_get_late_value",string='En retard')
    dispo_move = fields.Boolean(compute="_get_dispo_move",string='Mvt de disponibilité(Planning)')


    @api.multi
    def _check_date_stop(self) :
        for move in self:
            if move.date_stop and move.date_stop < move.date_start:
                return False
        return True
    
    _constraints = [(_check_date_stop, 'Erreur : La date de fin du mouvement doit être > à sa date de début !', ['date_stop'])
                    ]

    def _check_disponibility(self,vehicle_id,date_start,date_stop):
        model, dispo_move_name_id = self.env['ir.model.data'].get_object_reference('fleet', 'fleet_vehicle_move_location0')
        ignored_move_ids = [self.id]
        ignored_move_ids.extend(self.search([('name.id','=',dispo_move_name_id)]).ids)
        ignored_move_ids = list(set(ignored_move_ids))
        context = dict(self.env.context,ignored_move_ids=ignored_move_ids)
        self.env.context = context
        vehicle = self.env['fleet.vehicle'].browse(vehicle_id)
        used = vehicle.is_used(date_start,date_stop)[0] 
        if used:
            raise UserError(_("Le matériel %s n'est pas disponible dans l'interval de temps spécifié")%(vehicle.name))


    @api.model
    def create(self, vals):
        if ('code' not in vals) or (vals.get('code') == '/'):
            vals['code'] = self.env['ir.sequence'].next_by_code('fleet.vehicle.move')
        
        
        prev_move = self.env["fleet.vehicle"].browse(vals.get('vehicle_id')).last_move_id
        
        #disponibility_check_ok une variable pour permettre la création des OR même s'il existe un mouvement de location.La variable permet d'ignorer la vérification de la disponibilité
        disponibility_check_ok = self.env.context.get("disponibility_check_ok") or False
        print("***************",disponibility_check_ok)
        if not disponibility_check_ok:
            self._check_disponibility(vals.get('vehicle_id'),vals.get('date_start'),vals.get('date_stop'))
        
        move = super(FleetVehicleMove,self).create(vals)
        self.create_link(prev_move, move)
        return move

    @api.multi
    def write(self, vals):
        result = super(FleetVehicleMove,self).write(vals)
        
        disponibility_check_ok = self.env.context.get("disponibility_check_ok") or False
        print("***************",disponibility_check_ok)
        for move in self:
            date_start = vals.get('date_start') or move.date_start
            date_stop = vals.get('date_stop') or move.date_stop
            if not disponibility_check_ok:
                move._check_disponibility(move.vehicle_id.id,date_start,date_stop)
            
            if move.contract_id and move.contract_id.vehicle_position_id == move:
                write_data = {}
                write_data['start_date'] = date_start
                write_data['expiration_date'] = date_stop
                self.env.context = dict(self.env.context,from_move_update = 1)
                move.contract_id.write(write_data)
        return result


    @api.multi
    def unlink(self):
        for rec in self:
            if rec.state== 'done' and self._uid != SUPERUSER_ID:
                raise UserError(_("Vous n'avez pas les accès pour supprimer un mouvement"))
        return models.Model.unlink(self)
    
    @api.onchange('vehicle_id')
    def onchange_vehicle_id(self):
        self.model_id = self.vehicle_id.model_id.id
        self.category_id = self.vehicle_id.category_id.id
        self.license_plate = self.vehicle_id.license_plate
        self.lot = self.vehicle_id.lot
        self.odometer_start = self.vehicle_id.odometer
    
    @api.onchange('contract_id')
    def onchange_contract_id(self):
        model, cd_model_id = self.env['ir.model.data'].get_object_reference('fleet', 'fleet_vehicle_move_type_cd')
        model, ld_model_id = self.env['ir.model.data'].get_object_reference('fleet', 'fleet_vehicle_move_type_ld')
        if self.contract_id.contract_cd:
            self.doc_type_id = cd_model_id
        elif self.contract_id:
            self.doc_type_id = ld_model_id
        if self.contract_id:
            self.vehicle_id = self.contract_id.vehicle_id.id
        self.src_agence_id = self.contract_id.agence_id.id or self.contract_id.src_agence_id.id
        self.dest_agence_id = self.contract_id.ret_dest_agence_id.id or self.contract_id.dest_agence_id.id
        self.date_start = self.contract_id.start_date 
        self.date_stop = self.contract_id.expiration_date 
        
    @api.onchange('partner_id')
    def onchange_partner_id(self):
        address = ''
        if self.partner_id.street:
            address = self.partner_id.street+"\n"
        if self.partner_id.street2:
            address += self.partner_id.street2+"\n"
        if self.partner_id.zip:
            address += self.partner_id.zip+"\t"
        if self.partner_id.city_id:
            address += self.partner_id.city_id.name+"\t"
        if self.partner_id.country_id:
            address += self.partner_id.country_id.name
        self.partner_address = address

    @api.onchange('dp_src_partner_id')
    def onchange_dp_src_partner_id(self):
        address = ''
        if self.dp_src_partner_id.street:
            address = self.dp_src_partner_id.street+"\n"
        if self.dp_src_partner_id.street2:
            address += self.dp_src_partner_id.street2+"\n"
        if self.dp_src_partner_id.zip:
            address += self.dp_src_partner_id.zip+"\t"
        if self.dp_src_partner_id.city_id:
            address += self.dp_src_partner_id.city_id.name+"\t"
        if self.dp_src_partner_id.country_id:
            address += self.dp_src_partner_id.country_id.name
        self.dp_src_address = address

    @api.onchange('dp_dest_partner_id')
    def onchange_dp_dest_partner_id(self):
        address = ''
        if self.dp_dest_partner_id.street:
            address = self.dp_dest_partner_id.street+"\n"
        if self.dp_dest_partner_id.street2:
            address += self.dp_dest_partner_id.street2+"\n"
        if self.dp_dest_partner_id.zip:
            address += self.dp_dest_partner_id.zip+"\t"
        if self.dp_dest_partner_id.city_id:
            address += self.dp_dest_partner_id.city_id.name+"\t"
        if self.dp_dest_partner_id.country_id:
            address += self.dp_dest_partner_id.country_id.name
        self.dp_dest_address = address

    @api.onchange('driver_id')
    def onchange_driver_id(self):
        address = ''
        if self.driver_id.street:
            address = self.driver_id.street+"\n"
        if self.driver_id.street2:
            address += self.driver_id.street2+"\n"
        if self.driver_id.zip:
            address += self.driver_id.zip+"\t"
        if self.driver_id.city_id:
            address += self.driver_id.city_id.name+"\t"
        if self.driver_id.country_id:
            address += self.driver_id.country_id.name
        self.driver_address = address

    @api.onchange('product_id')
    def onchange_product_id(self):
        self.uom_id = self.product_id.uom_id.id
        self.default_code = self.product_id.default_code
        
    @api.multi
    def action_done(self):
        data = {'state':'done', 'close':True}
        if not self.date_stop:
            data['date_stop'] = fields.Datetime.now()
        
        """
        vehicle   = self.vehicle_id
        
        draft_ids = self.env['fleet.vehicle.move'].search([('id','!=',self.id),('vehicle_id','=',vehicle.id),('state','=','draft')])
        if model == 'fleet.vehicle.move.location':
            if not draft_ids:##Si aucun mouvement n'est en cours alors on indique que le materiel est disponible
                if model_id:
                    data = {"name" :model_id,'date_start':fields.Datetime.now(),'vehicle_id':vehicle.id}
                    self.env['fleet.vehicle.move'].create(data)
                else:
                    raise osv.except_osv(u'Erreur !', u'Erreur emplacement arrivé.')
        """
        return self.write(data)
    
    
