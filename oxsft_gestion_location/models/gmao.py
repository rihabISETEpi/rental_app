# -*- coding: utf-8 -*-



from dateutil import relativedelta

#from fleet import MAINTENANCE_TYPE_SELECTION1 ++zart
#from formatDate import formatDate, formatDatetime ++zart
from odoo import models, fields, api, _
from odoo.exceptions import UserError

MAINTENANCE_TYPE_SELECTION1 = [
                               ('bm', 'Panne'),
                               ('cm', 'Corrective'),
                               ('pm', 'Programmée'),
                               ]

UNITE_SELECTION = [
                   ('annee','Année'),('mois','Mois'),
                   ('days', 'Jours'),('horaire','Heure'),
                   ('km', 'Km')
                  ]
ECART_SELECTION=  [
                   ('%','%'),
                   ('valeur','Valeur')
                  ]

SELECTION_DICT = {
                  'annee': 'Ans',
                  'mois':"Mois",
                  'days':"Jours",
                  "horaire":"Heures",
                  "km":"Km"
                  }
SELECTION_DICT2 = {
                   'annee': 'Année(s)',
                   'mois':"Mois",
                   'days':"Jour(s)",
                   "horaire":"Heure(s)",
                   "km":"Km"
                   }



##WIZARD PERMETTANT DE FAIRE LE LIEN ENTRE DEUX MODÈLE DE MAINTENANCE
class TmsGmaoPmModelLink(models.TransientModel):
    _name = "tms.gmao.pm.model.link"

    @api.model
    def _default_active_model_id(self):
        active_id = self.env.context.get('active_id') 
        return active_id

    pm_model_id1 = fields.Many2one('tms.gmao.pm.model','Modèle 1',required=True)
    pm_model_id2 = fields.Many2one('tms.gmao.pm.model',"Modèle 2",required=True)
    active_model_id = fields.Many2one('fleet.vehicle.model','Modèle',required=True,default=_default_active_model_id)

    

    @api.multi
    def action_valider(self):
        data = self
        if data.pm_model_id1.service_type_id.id != data.pm_model_id2.service_type_id.id:
            raise UserError('Erreur', "Les deux modèles doivent avoir le même type d'intervention") 
        data.pm_model_id1.pm_model_id.write({'pm_model_id':False})
        data.pm_model_id2.pm_model_id.write({'pm_model_id':False})
        data.pm_model_id1.write({'pm_model_id':data.pm_model_id2.id})
        data.pm_model_id2.write({'pm_model_id':data.pm_model_id1.id})

class TmsGmaoPmModelTemplate(models.Model):
    _name = "tms.gmao.pm.model.template"

    @api.multi
    @api.depends('meter','meter_ecart','meter_ecart0','valeur_ecart','interval')
    def _get_warn_period(self):
        for rec in self:
            warning = 0
            if rec.meter_ecart == 'valeur':
                if rec.meter_ecart0 == "annee":
                    warning = rec.valeur_ecart * 365
                elif rec.meter_ecart0 == "mois":
                    warning = rec.valeur_ecart * 30 
                elif rec.meter_ecart0 == "horaire":
                    warning = rec.valeur_ecart / 24
                else:
                    warning = rec.valeur_ecart                
            else:
                if rec.meter == "annee":
                    warning = (rec.valeur_ecart/100) * rec.interval * 365
                elif rec.meter == "mois":
                    warning = (rec.valeur_ecart/100) * rec.interval *30
                elif rec.meter == "horaire":
                    warning = (rec.valeur_ecart/100) * rec.interval / 24
                else:
                    warning = (rec.valeur_ecart/100) * rec.interval
            rec.warning = warning

    name = fields.Char('Libellé', required=True,default=lambda self: self.env['ir.sequence'].next_by_code('tms.gmao.pm.model.template'))
    description = fields.Text('Description')
    service_type_id = fields.Many2one('fleet.service.type', string="Type d'intervention", domain=[('mro_ok','=',True)])
    meter = fields.Selection(UNITE_SELECTION, 'Unité', required=True,default="days")
    periodic = fields.Boolean('Périodique ?', help="Cochez cette option si la maintenance programmée est periodique.",default=True)
    interval = fields.Integer('Périodicité :', help="Temps avant la prochaine maintenance.")
    warning = fields.Integer(compute="_get_warn_period",string='Alerte à :')
    first_interval = fields.Integer('1 ère échéance  :')
    meter_ecart0 = fields.Selection(UNITE_SELECTION, "Unité de l'écart" , required=True)
    meter_ecart = fields.Selection(ECART_SELECTION, 'Type d’écart :')
    valeur_ecart = fields.Float('Valeur en - ')
    line_ids = fields.One2many("fleet.line.reparation","pm_model_template_id","Pièces de rechange")

    @api.onchange('meter')
    def onchange_meter(self): 
        self.meter_ecart0 = self.meter

    @api.onchange('meter_ecart0')
    def onchange_meter_ecart0(self): 
        if self.meter_ecart0 == 'km' and self.meter != 'km':
            raise UserError(_("Les unités n'appartiennent pas à la même catégorie"))
        elif self.meter_ecart0 != 'km' and self.meter == 'km':
            raise UserError(_("Les unités n'appartiennent pas à la même catégorie"))
        
    
    @api.model
    def create(self,vals):
        el_id = super(TmsGmaoPmModelTemplate,self).create(vals)
        element  = el_id
        if element.meter_ecart0 == 'km' and element.meter != 'km':
            raise UserError(_("Les unités n'appartiennent pas à la même catégorie"))
        elif element.meter_ecart0 != 'km' and element.meter == 'km':
            raise UserError(_("Les unités n'appartiennent pas à la même catégorie"))
        return el_id

    @api.multi
    def write(self,vals):
        result = super(TmsGmaoPmModelTemplate,self).write(vals)
        for element in self:
            if element.meter_ecart0 == 'km' and element.meter != 'km':
                raise UserError(_("Les unités n'appartiennent pas à la même catégorie"))
            elif element.meter_ecart0 != 'km' and element.meter == 'km':
                raise UserError(_("Les unités n'appartiennent pas à la même catégorie"))
        return result


class TmsGmaoPmModel(models.Model):
    _name = "tms.gmao.pm.model"

    @api.multi
    @api.depends('meter','meter_ecart','meter_ecart0','valeur_ecart','interval')
    def _get_warn_period(self):
        for rec in self:
            warning = 0
            if rec.meter_ecart == 'valeur':
                if rec.meter_ecart0 == "annee":
                    warning = rec.valeur_ecart * 365
                elif rec.meter_ecart0 == "mois":
                    warning = rec.valeur_ecart * 30 
                elif rec.meter_ecart0 == "horaire":
                    warning = rec.valeur_ecart / 24
                else:
                    warning = rec.valeur_ecart                
            else:
                if rec.meter == "annee":
                    warning = (rec.valeur_ecart/100) * rec.interval * 365
                elif rec.meter == "mois":
                    warning = (rec.valeur_ecart/100) * rec.interval *30
                elif rec.meter == "horaire":
                    warning = (rec.valeur_ecart/100) * rec.interval / 24
                else:
                    warning = (rec.valeur_ecart/100) * rec.interval
            rec.warning = warning

    name = fields.Char('Libellé', required=True)
    description = fields.Text('Description :')
    service_type_id = fields.Many2one('fleet.service.type', string="Type d'intervention", domain=[('mro_ok','=',True)])
    meter = fields.Selection(UNITE_SELECTION, 'Unité', required=True,default="days")
    periodic = fields.Boolean('Périodique ?', help="Cochez cette option si la maintenance programmée est periodique.",default=True)
    interval = fields.Integer('Périodicité :', help="Temps avant la prochaine maintenance.")
    warning = fields.Integer(compute="_get_warn_period",string='Alerte à :')
    first_interval = fields.Integer('1 ère échéance  :')
    meter_ecart0 = fields.Selection(UNITE_SELECTION, "Unité de l'écart" , required=True)
    meter_ecart = fields.Selection(ECART_SELECTION, 'Type d’écart :')
    valeur_ecart = fields.Float('Valeur en - ')
    pm_model_id = fields.Many2one('tms.gmao.pm.model',"Modèle lié")
    model_id = fields.Many2one('fleet.vehicle.model',"Modèle")
    model_template_id = fields.Many2one('tms.gmao.pm.model.template','Template')
    line_ids = fields.One2many("fleet.line.reparation","pm_model_id","Pièces de rechange")

    _sql_constraints = [
        ('name_uniq', 'unique(id)', "La référence doit être unique !")
    ]

    @api.onchange('model_template_id')
    def on_change_model_template_id(self):
        model_template_read = self.model_template_id.read()
        data = {}
        if len(model_template_read) > 0:
            data = model_template_read[0]
        
        data['create_uid'] = False
        data['write_uid'] = False
        return {'value':data}
    
    @api.onchange("meter")
    def onchange_meter(self): 
        if not self.meter_ecart0:
            self.meter_ecart0 =self.meter

    @api.onchange("meter_ecart0")
    def onchange_meter_ecart0(self): 
        if self.meter_ecart0 == 'km' and self.meter != 'km':
            raise UserError(_("Les unités n'appartiennent pas à la même catégorie"))
        elif self.meter_ecart0 != 'km' and self.meter == 'km':
            raise UserError(_("Les unités n'appartiennent pas à la même catégorie"))
    
    @api.model
    def create(self,vals):
        el_id = super(TmsGmaoPmModel,self).create(vals)
        element  = el_id
        if element.meter_ecart0 == 'km' and element.meter != 'km':
            raise UserError("Les unités n'appartiennent pas à la même catégorie")
        elif element.meter_ecart0 != 'km' and element.meter == 'km':
            raise UserError("Les unités n'appartiennent pas à la même catégorie")
        return el_id

    @api.multi
    def write(self,vals):
        result = super(TmsGmaoPmModel,self).write(vals)
        for element in self:
            if element.meter_ecart0 == 'km' and element.meter != 'km':
                raise UserError(_("Les unités n'appartiennent pas à la même catégorie"))
            elif element.meter_ecart0 != 'km' and element.meter == 'km':
                raise UserError(_("Les unités n'appartiennent pas à la même catégorie"))
        return result

    @api.multi
    @api.returns('self', lambda value:value.id)
    def copy(self, default=None):
        default = {'model_id':False,'pm_model_id':False}
        return models.Model.copy(self, default=default)

##WIZARD PERMETTANT DE FAIRE LE LIEN ENTRE DEUX ALERTES
class TmsGmaoPmLink(models.TransientModel):
    _name = "tms.gmao.pm.link"

    @api.model
    def _default_vehicle_id(self):
        active_id = self.env.context and self.env.context.get('active_id') 
        active = self.env['tms.gmao.pm'].browse(active_id)
        return active and active.vehicle_id.id or False
    
    @api.model
    def _default_service_type_id(self):
        active_id = self.env.context and self.env.context.get('active_id') 
        active = self.env['tms.gmao.pm'].browse(active_id)
        return active and active.service_type_id.id or False
    
    @api.model
    def _default_active_pm_id(self):
        active_id = self.env.context and self.env.context.get('active_id') 
        return active_id

    linked_pm_id = fields.Many2one('tms.gmao.pm','Alerte cible')
    vehicle_id = fields.Many2one('fleet.vehicle','Véhicule',default=_default_vehicle_id)
    service_type_id = fields.Many2one('fleet.service.type',"Type d'intervention",default=_default_service_type_id)
    active_pm_id = fields.Many2one('tms.gmao.pm','Alerte source',default=_default_active_pm_id)


    @api.multi
    def action_valider(self):
        data = self
        seq = self.env['ir.sequence'].next_by_code('alert.link')
        data.active_pm_id.pm_id.write({'pm_id':False,'id_linked':False})
        data.active_pm_id.write({'pm_id':data.linked_pm_id.id,'name_linked':seq})
        data.linked_pm_id.write({'pm_id':data.active_pm_id.id,'name_linked':seq})



class TmsGmaoPm(models.Model):
    ###"""Maintenance préventive"""
    _name = "tms.gmao.pm"
    _inherit = 'mail.thread'
    _description = "Maintenance préventive"
    _order="create_date desc"

    @api.multi
    def name_get(self):
        result = []
        for record in self:
            name = record.name
            if record.description:
                name  = name+ "( "+record.description+" )"
            else :
                name = name+ "( "+str(record.interval) + " "+ SELECTION_DICT.get(record.meter)+" )"
            result.append((record.id, name))
        return result

    def get_2pm_linked(self,pm_id1,pm_id2):
        seq = self.env['ir.sequence'].next_by_code('alert.link')
        self.browse(pm_id1).write({'pm_id':pm_id2,'name_linked':seq})
        self.browse(pm_id2).write({'pm_id':pm_id1,'name_linked':seq})

    @api.multi
    def unlink(self):
        ###"""Méthode de suppression"""
        for prog in self:
            if prog.state != 'draft':
                raise UserError(_(u'Vous ne pouvez pas supprimer une maintenance programmée, songez à l\'annuler'))
        return super(TmsGmaoPm, self).unlink()

    @api.multi
    @api.depends("service_type_id")
    def _get_type_alert(self):
        ###"""Type d'alerte"""
        for record in self:
            record.type_alert = record.service_type_id and record.service_type_id.name or ''

    @api.onchange('service_type_id')
    def onchange_service_type_id(self):
        self.periodic = True
        if self.service_type_id.maintenance_type == 'garantie':
            self.periodic = False
            
    @api.multi
    @api.depends('alert_ids.state','alert_ids.state_process','alert_ids.left','alert_ids')
    def _get_information_alert(self):
        ##"""Récupérer les données des alertes"""
        alert_obj = self.env['tms.gmao.pm.alert']
        for pm in self:
            pm.state = 'waiting' if pm.service_type_id.code == 'ctrlapol' else 'draft'
            alert_ids = alert_obj.search([('pm_id','=',pm.id),('state_process','=','progress')],order="id desc")
            if alert_ids:
                last_object_alert_pm = alert_ids[0]
                if last_object_alert_pm:
                    if pm.meter in ('annee','mois','days','horaire'):
                        pm.days_next_due = last_object_alert_pm.days_next_due
                        pm.left = last_object_alert_pm.left
                    if pm.meter== 'km':
                        pm.km_next_due = last_object_alert_pm.km_next_due
                        pm.left = last_object_alert_pm.left
                    pm.state = last_object_alert_pm.state
            else:
                nbr_alert=alert_obj.search_count([('pm_id','=',pm.id)])
                if nbr_alert:
                    pm.state = 'done'


    @api.multi
    @api.depends("vehicle_id","vehicle_id.odometer")
    def _get_counter_current(self):
        for record in self:
            record.counter_current = record.vehicle_id.odometer
            
    
    @api.multi
    def end_periodic(self):
        self.write({'periodic': False})
        return True

    @api.multi
    def end_pm(self):
        alert_obj = self.env["tms.gmao.pm.alert"]
        self.end_periodic()
        for pm in self:
            ids_search_pm_alert = alert_obj.search([('pm_id','=',pm.id),('state_process','=','progress')])
            if ids_search_pm_alert:
                ids_search_pm_alert.action_cancel_alert()   
        return True

    @api.multi
    def generate_alert(self):
        ###"""Générer l'alerte"""
        for object_pm in self:
            data={}
            if object_pm.meter == 'km':
                data={
                          'pm_id': object_pm.id,
                          'date': fields.Datetime.now(),
                          'interval': object_pm.first_interval,
                          'km_last_done': object_pm.km_last_done,
                          'warn_period': object_pm.warn_period,
                          'state_process': 'progress',
                          'description' : object_pm.description,
                    }
            elif object_pm.meter in ('annee','mois','days','horaire'):
                data={
                          'pm_id': object_pm.id,
                          'date': fields.Datetime.now(),
                          'interval': object_pm.first_interval,
                          'days_last_done': object_pm.days_last_done,
                          'warn_period': object_pm.warn_period,
                          'state_process': 'progress',
                          'description' : object_pm.description,
                     }
                
            ctx = dict(self.env.context,alert_ok=True)
            self.env.context = ctx
            self.env['tms.gmao.pm.alert'].create(data)
            object_pm.write({'draft_ok':False})
        return True

    @api.multi
    @api.depends('interval','km_last_done','km_next_due','days_last_done','days_next_due','warn_period','left')
    def _get_info_alert_view(self):
        u"""Récupération des données (km/jours) de l'alerte"""
        for object_pm in self:
            interval_view = last_done_view = next_due_view = warn_period_view = left_view = ""
            if object_pm.meter=='km':
                interval_view = '%d Km' %(object_pm.interval or 0)
                last_done_view = '%d Km' %(object_pm.km_last_done or 0)
                next_due_view = '%d Km' %(object_pm.km_next_due or 0)
                warn_period_view = '%d Km' %(object_pm.warn_period or 0)
                left_view = '%d Km' %(object_pm.left or 0)
            elif object_pm.meter in ('annee','mois','days','horaire'):
                label = object_pm.meter
                interval_view = '%d %s' %(object_pm.interval or 0,SELECTION_DICT2.get(label).decode('utf-8'))
                
                ####FORMATER LES DATE AU 
                #days_last_done  = formatDate(self,object_pm.days_last_done) if object_pm.days_last_done  else u'Non défini' ++zart
                #days_next_due = formatDate(self,object_pm.days_next_due) if object_pm.days_next_due else u'Non défini' ++zart
                days_last_done = fields.Datetime.to_string(object_pm.days_last_done) if object_pm.days_last_done else 'Non défini'
                days_next_due = fields.Datetime.to_string(object_pm.days_next_due) if object_pm.days_next_due else 'Non défini'
                ####FORMATER LES DATES %d/%m/%Y     formatDate a été créé dans le module
                last_done_view = '%s' %(days_last_done)
                next_due_view = '%s' %(days_next_due)
                warn_period_view = '%d Jour(s)' %(object_pm.warn_period or 0)
                left_view = '%d Jour(s)' %(object_pm.left or 0)
            object_pm.interval_view = interval_view
            object_pm.last_done_view = last_done_view
            object_pm.next_due_view = next_due_view
            object_pm.warn_period_view = warn_period_view
            object_pm.left_view = left_view


    @api.multi
    @api.depends('meter','meter_ecart','meter_ecart0','valeur_ecart','interval')
    def _get_warn_period(self):
        for rec in self:
            warning = 0
            if rec.meter_ecart == 'valeur':
                if rec.meter_ecart0 == "annee":
                    warning = rec.valeur_ecart * 365
                elif rec.meter_ecart0 == "mois":
                    warning = rec.valeur_ecart * 30 
                elif rec.meter_ecart0 == "horaire":
                    warning = rec.valeur_ecart / 24
                else:
                    warning = rec.valeur_ecart                
            else:
                if rec.meter == "annee":
                    warning = (rec.valeur_ecart/100) * rec.interval * 365
                elif rec.meter == "mois":
                    warning = (rec.valeur_ecart/100) * rec.interval *30
                elif rec.meter == "horaire":
                    warning = (rec.valeur_ecart/100) * rec.interval / 24
                else:
                    warning = (rec.valeur_ecart/100) * rec.interval
            rec.warn_period = warning

    name = fields.Char('Réf MP', size=20,default=lambda self: self.env['ir.sequence'].next_by_code('tms.gmao.pm'))
    vehicle_id = fields.Many2one('fleet.vehicle', 'Véhicule')
    type_alert = fields.Char(compute="_get_type_alert",string='Type alerte', store=True)
    description = fields.Char('Libellé Alerte')
    service_type_id = fields.Many2one('fleet.service.type', string="Type d'intervention", domain=[('mro_ok','=',True)])
    meter = fields.Selection(UNITE_SELECTION, 'Unité', required=True,default="days")
    periodic = fields.Boolean('Périodique ?', help="Cochez cette option si la maintenance programmée est periodique.",default=True)
        
    interval = fields.Integer('Périodicité', help="Ecart entre deux maintenances.")
    days_last_done = fields.Date('Commencer le', required=True,default=fields.Date.context_today)
    days_next_due = fields.Date(compute="_get_information_alert",string='Prochaine date')
    warn_period = fields.Integer(compute="_get_warn_period",string='Alerte en -',store=True)
    left = fields.Integer(compute="_get_information_alert",string='Restant')
    first_interval = fields.Integer('1 ère échéance   :')
    km_last_done = fields.Float('Commencer à',required=True)
    km_next_due = fields.Integer(compute="_get_information_alert",string='Prochain km')
        
    interval_view = fields.Char(compute="_get_info_alert_view",string='Intervalle')
    last_done_view = fields.Char(compute="_get_info_alert_view", string='Commence')
    next_due_view = fields.Char(compute="_get_info_alert_view", string='Termine')
    warn_period_view = fields.Char(compute="_get_info_alert_view",string='Alerte en -',store=True)
    left_view = fields.Char(compute="_get_info_alert_view", string='Restant')
    counter_current = fields.Float(compute="_get_counter_current",string="Kilométrage actuel",store=True)
    draft_ok = fields.Boolean('Brouillon de création',default=True)
    state = fields.Selection([('waiting',"Attene d'une autre opération"),('draft', 'Normal'),
                                    ('left', 'Dépassé'),
                                    ('alert', 'Alerte'),
                                    ('done', 'Terminé')], string='Statut',compute="_get_information_alert",store=True)
                                  
    alert_ids = fields.One2many('tms.gmao.pm.alert', 'pm_id', 'Suivi des alertes')
    meter_ecart0 = fields.Selection(UNITE_SELECTION, "Unité de l'écart" , required=True)
    meter_ecart = fields.Selection(ECART_SELECTION, 'Type d’écart:')
    valeur_ecart = fields.Float('Valeur en - ')
    maintenance_type = fields.Selection(MAINTENANCE_TYPE_SELECTION1,related='service_type_id.maintenance_type',string='Type de maintenance')
    pm_id = fields.Many2one('tms.gmao.pm','Alerte liée')
    name_linked = fields.Char('Numéro Liaison',readonly=True)
        
    pm_model_id = fields.Many2one('tms.gmao.pm.model',"Modèle d'alerte")##Le modèle de maintenance qui a permis la génération de cette alerte
        
    model_template_id = fields.Many2one('tms.gmao.pm.model.template',"Modèle d'alerte")
        
    line_ids = fields.One2many("fleet.line.reparation","pm_id","Pièces de rechange")

    @api.onchange('model_template_id')
    def on_change_model_template_id(self):
        model_template_read = self.model_template_id.read()
        data = {}
        if len(model_template_read) > 0:
            data = model_template_read[0]
        
        data['create_uid'] = False
        data['write_uid'] = False
        return {'value':data}

    @api.onchange("vehicle_id")
    def onchange_vehicle_id(self):
        u"""Évènement lors du changement du véhicule"""
        self.km_last_done = self.vehicle_id.odometer
    
    @api.onchange('meter')
    def onchange_meter(self): 
        self.meter_ecart0 = self.meter

    @api.onchange('meter_ecart0')
    def onchange_meter_ecart0(self): 
        if self.meter_ecart0 == 'km' and self.meter != 'km':
            raise UserError(_("Les unités n'appartiennent pas à la même catégorie"))
        elif self.meter_ecart0 != 'km' and self.meter == 'km':
            raise UserError(_("Les unités n'appartiennent pas à la même catégorie"))
    
    @api.model
    def create(self,vals):
        el_id = super(TmsGmaoPm,self).create(vals)
        element  = el_id
        if element.meter_ecart0 == 'km' and element.meter != 'km':
            raise UserError(_("Les unités n'appartiennent pas à la même catégorie"))
        elif element.meter_ecart0 != 'km' and element.meter == 'km':
            raise UserError(_("Les unités n'appartiennent pas à la même catégorie"))
        return el_id

    @api.multi
    def write(self,vals):
        result = super(TmsGmaoPm,self).write(vals)
        for element in self:
            if element.meter_ecart0 == 'km' and element.meter != 'km':
                raise UserError(_("Les unités n'appartiennent pas à la même catégorie"))
            elif element.meter_ecart0 != 'km' and element.meter == 'km':
                raise UserError(_("Les unités n'appartiennent pas à la même catégorie"))
        return result
    

class TmsGmaoPmAlert(models.Model):
    ###"""Alertes"""
    _name = "tms.gmao.pm.alert"
    _description = u"Suivi des alertes maintenance périodiques"
    _order = "date desc"

    @api.multi
    def name_get(self):
        result = []
        for record in self:
            name = record.name
            if record.description:
                name  = name+ "( "+record.description+" )"
            else :
                name = name+ "( "+str(record.interval) + " "+ SELECTION_DICT.get(record.meter).decode('utf-8')+" )"
            result.append((record.id, name))
        return result

    @api.model
    def create(self,vals):
        ###"""Méthode de création"""
        context = self.env.context
        if context:
            flag_alert = context.get('alert_ok', False)
            if flag_alert:
                id_alert = super(TmsGmaoPmAlert, self).create(vals)
                return id_alert
            else:
                raise UserError(_('Pour créer une alerte, veuillez créer une maintenance programmée.'))
        else:
            raise UserError(_('Pour créer une alerte, veuillez créer une maintenance programmée.'))

    @api.multi
    def unlink(self):
        ##"""Méthode de suppression"""
        raise UserError(_(u'Vous ne pouvez pas supprimer une alerte, songez à l\'annuler.'))

    @api.multi
    @api.returns('self', lambda value:value.id)
    def copy(self, default=None):
        if default is None:
            default = {}
        default = default.copy()
        default['name'] = self.env['ir.sequence'].next_by_code('tms.gmao.pm.alert')
        default['maintenance_ids']=[]
        #default['maintenance_group_ids']=[]
        default['state'] = 'draft'
        return super(TmsGmaoPmAlert, self).copy(default)   

    @api.multi
    @api.depends('interval','days_last_done','km_last_done')
    def _value_next_due(self):
        ###"""Calcul des prochaines données d'alerte"""
        for record in self:
            days_next_due = False
            km_next_due = 0
            
            if (record.meter == "annee"):
                interval = relativedelta.relativedelta(days=record.interval*365)
                last_done = fields.Date.from_string(record.days_last_done)
                days_next_due = last_done + interval
            elif (record.meter == "mois"):
                interval = relativedelta.relativedelta(days=record.interval*30)
                last_done = fields.Date.from_string(record.days_last_done)
                days_next_due = last_done + interval
            elif (record.meter == "days"):
                interval = relativedelta.relativedelta(days=record.interval)
                last_done = fields.Date.from_string(record.days_last_done)
                days_next_due = last_done + interval
            elif (record.meter == "horaire"):
                interval = relativedelta.relativedelta(days=record.interval/24)
                last_done = fields.Date.from_string(record.days_last_done)
                days_next_due = last_done + interval
            elif (record.meter == "km"):
                km_next_due=record.km_last_done + record.interval
                
            record.days_next_due = days_next_due
            record.km_next_due = km_next_due

    @api.multi
    @api.depends('state_process','meter','days_next_due','pm_id','vehicle_id','km_next_due')
    def _value_due(self):
        ###"""Calcul du temps/km restant"""
        for record in self:
            left = 0
            if record.state_process == 'progress':
                if record.meter in ("annee","mois","days","horaire"):
                    next_due = fields.Date.from_string(record.days_next_due)
                    NOW = fields.Date.from_string(fields.Date.context_today(self))
                    due_days = next_due - NOW
                    left= due_days.days
                elif record.pm_id:
                    if record.pm_id.meter == "km":
                        current_km=0
                        if record.vehicle_id:
                            current_km = record.vehicle_id.odometer
                        left = record.km_next_due - current_km
            record.left = left

    @api.multi
    def action_done_alert(self):
        ###"""Valider l'alerte"""
        object_pm_alert = self
        context = dict(self.env.context, active_id=object_pm_alert.id, active_model=self._name)
        if not object_pm_alert.vehicle_id:
            return False
        km = object_pm_alert.vehicle_id.odometer


        data_alert_process = {
                            'vehicle_id': object_pm_alert.vehicle_id and object_pm_alert.vehicle_id.id or False,
                            'periodic_ok': object_pm_alert.periodic,
                            'alert_id': object_pm_alert.id,    
                            'km': km,
                            'meter': object_pm_alert.meter,
                            'description':object_pm_alert.description,   

                            }

        line_ids =[]
        for filtre_line in object_pm_alert.pm_id.line_ids:
            data = (0,0,{'product_id':filtre_line.product_id.id,'product_qty':filtre_line.product_qty})
            line_ids.append(data)
        data_alert_process['line_ids'] = line_ids
        alert_process_id = self.env["tms.gmao.pm.alert.process"].create(data_alert_process)
        alert_view_id = self.env['ir.ui.view'].search([('model','=','tms.gmao.pm.alert.process')])
        alert_name='Assistant Ordre de maintenance'
        alert_res_model='tms.gmao.pm.alert.process'
        
        if alert_process_id:
            return {
                    'name': alert_name,
                    'view_mode': 'form',
                    'view_id': alert_view_id.id,
                    'view_type': 'form',
                    'res_model': alert_res_model,
                    'res_id': alert_process_id.id,
                    'type': 'ir.actions.act_window',
                    'nodestroy': True,
                    'target': 'new',
                    'domain': '[]',
                    'context': context,
                    }
        return True
    
    @api.multi
    def action_cancel_alert(self):
        ###"""Annuler l'alerte"""
        mro_obj = self.env['mro.order']
        for object_alert in self:
            if object_alert.state_process == 'progress':
                search_mro_orders = mro_obj.search([('alert_id','=',object_alert.id),('state','!=','done')])
                for mro in search_mro_orders:
                    #workflow.trg_validate(self.env.user.id, "mro.order", mro.id, "button_cancel", self.env.cr) ++zart
                    self.env['mro.order'].button_cancel([mro.id]) #++zart
                object_alert.write({'state_process':'cancel'})
        return True

    @api.multi
    def validate_alert(self,periodic=True,date=False,km=False):
        ###"""valider l'alerte"""
        object_alert = self
        if object_alert:
            data_write={
                        'state_process' : 'done',
                        }
            object_alert.write(data_write)
            #create new alert
            if object_alert.pm_id:
                if object_alert.periodic == True:
                    if periodic==False:
                        object_alert.pm_id.write({'periodic' :False})
                    elif periodic:
                        if object_alert.meter == 'km':
                            km_last_done= object_alert.km_next_due
                            if km!=False :
                                km_last_done=km
                            else:
                                km_last_done = object_alert.vehicle_id and object_alert.vehicle_id.odometer or 0
                            data={
                                      'pm_id' : object_alert.pm_id.id,
                                      'date' : date,
                                      'interval' : object_alert.pm_id.interval,
                                      'km_last_done' : km_last_done,
                                      'warn_period' : object_alert.warn_period,
                                      'state_process' : 'progress',
                                      'description' : object_alert.pm_id.description,
                                      }
                        elif object_alert.meter in ('annee','mois','days','horaire'):
                            if not date:
                                date=fields.Datetime.now()
                            data={
                                      'pm_id' : object_alert.pm_id.id,
                                      'date' : fields.Datetime.now(),
                                      'interval' : object_alert.pm_id.interval,
                                      'days_last_done' : date,
                                      'warn_period' : object_alert.warn_period,
                                      'description' : object_alert.pm_id.description,
                                      'state_process' : 'progress',
                                      'description' : object_alert.pm_id.description,
                                      }
                        ctx = dict(self.env.context,alert_ok=True)
                        self.env.context = ctx
                        self.env['tms.gmao.pm.alert'].create(data)
                else:
                    object_alert.pm_id.write({'periodic' : False})
                
            ###VERIFIER S'IL YA DES ALERTE EN ATTENTE D'UNE AUTRE OPÉRATION
            ### VALIDER LES ALERTE EN ATTENTE AVEC COMME DEBUT,LA FIN DU CONTROLE TECHNIQUE
            pm_obj = self.env['tms.gmao.pm']
            if object_alert.pm_id.service_type_id.code == 'ctrltech':
                anti_alert_ids = pm_obj.search([('vehicle_id','=',object_alert.vehicle_id.id),('service_type_id.code','=','ctrlapol'),('state','=','waiting')])
                for anti in anti_alert_ids:
                    if object_alert.meter == anti.meter :
                        if object_alert.meter == 'km':
                            anti.km_last_done = object_alert.km_next_due
                        else:
                            anti.days_last_done = fields.Datetime.now()
                    anti.generate_alert()
        return True

    @api.multi
    @api.depends("state_process","meter","left","warn_period")
    def _get_state(self):
        ###"""récupérer l'état"""
        for alert in self:  
            state = 'done'
            if alert.state_process == 'progress':            
                if alert.meter in ('annee','mois','days','horaire'):
                    if alert.left <= 0:
                        state = 'left'
                    elif alert.left <= alert.warn_period:
                        state = 'alert'
                    else:
                        state = 'draft'
                elif alert.meter == 'km':
                    if alert.left <= 0:
                        state = 'left'
                    elif alert.left <= alert.warn_period:
                        state = 'alert'
                    else:
                        state = 'draft'
            alert.state = state
    
    @api.multi
    @api.depends("pm_id")
    def _get_type_alert(self):
        ###"""récupérer le type d'alerte"""
        for alert in self:
            alert.type_alert = alert.pm_id.type_alert
    
    @api.multi
    @api.depends("meter","interval","km_last_done","km_next_due","days_last_done","days_next_due","warn_period","left")
    def _get_info_alert_view(self):
        ###"""récupérer les infos d'alerte"""
        for object_alert in self:
            interval_view = last_done_view = next_due_view = warn_period_view = left_view = ""
            if object_alert.meter=='km':
                interval_view = '%d Km' %(object_alert.interval or 0)
                last_done_view = '%d Km' %(object_alert.km_last_done or 0)
                next_due_view = '%d Km' %(object_alert.km_next_due or 0)
                warn_period_view = '%d Km' %(object_alert.warn_period or 0)
                left_view = '%d Km' %(object_alert.left or 0)

            elif object_alert.pm_id.meter in ('annee','mois','days','horaire'):
                label = object_alert.meter
                interval_view = '%d %s' %(object_alert.interval or 0,SELECTION_DICT2.get(label).decode('utf-8'))
                
                ###FORMATAGE %d/%m/%Y
                #days_next_due = formatDate(self,object_alert.days_next_due) if object_alert.days_next_due else u"Non défini" ++zart
                #days_last_done = formatDate(self,object_alert.days_last_done) if object_alert.days_last_done else u"Non défini" ++zart
                days_next_due = object_alert.days_next_due.strftime('%Y-%m-%d') if object_alert.days_next_due else 'Non défini'
                days_last_done = object_alert.days_last_done.strftime('%Y-%m-%d') if object_alert.days_last_done else 'Non défini'
                last_done_view = '%s' %days_last_done
                next_due_view = '%s' %days_next_due
                
                warn_period_view = '%d Jour(s)' %(object_alert.warn_period or 0)
                left_view = '%d Jour(s)' %(object_alert.left  or 0)

            object_alert.interval_view = interval_view
            object_alert.last_done_view = last_done_view
            object_alert.next_due_view = next_due_view
            object_alert.warn_period_view = warn_period_view
            object_alert.left_view = left_view
            
    

    name = fields.Char('Alerte', size=32,readonly=True,default=lambda self: self.env['ir.sequence'].next_by_code('tms.gmao.pm.alert'))
    date = fields.Datetime('Date',readonly=True,default=fields.Datetime.now)
    description = fields.Text('Description')
    pm_id = fields.Many2one('tms.gmao.pm', 'Maint. Prog.', required=True, readonly=True,ondelete="cascade")
    meter = fields.Selection(UNITE_SELECTION,related='pm_id.meter',string='Unité', store=True)
    vehicle_id = fields.Many2one('fleet.vehicle',related='pm_id.vehicle_id',string='Véhicule', readonly=True, store=True)
    license_plate = fields.Char(related='vehicle_id.license_plate', string='Immatriculation',readonly=True)
    periodic = fields.Boolean(related='pm_id.periodic', string='Périodique', readonly=True, store=True)
    maintenance_ids = fields.One2many('mro.order', 'alert_id', 'Maintenances', readonly=True)
    type_alert = fields.Char(compute="_get_type_alert", string="Type d’alerte", store=True)

        
    interval = fields.Integer('Périodicité', help="Ecart entre deux maintenances.")
    days_last_done = fields.Date('Commencer le',default=fields.Date.context_today)
    days_next_due = fields.Date(compute="_value_next_due",string='Prochaine date')
    warn_period = fields.Integer('Alerte en -',default=0)
    left = fields.Integer(compute="_value_due", string='Restant')
    first_interval = fields.Integer('1 ère échéance   :')
    km_last_done = fields.Float('Commencer à',required=True,default=0)
    km_next_due = fields.Integer(compute="_value_next_due", string='Prochain km')
        

    state_process = fields.Selection(
                                   [('progress', 'En cours'),
                                    ('done', 'Traité'),
                                    ('cancel', 'Annulé'),
                                    ], 'Traitement', required=True, readonly=True,default="progress"
                                   )
    interval_view = fields.Char(compute="_get_info_alert_view",string='Périodicité')
    last_done_view = fields.Char(compute="_get_info_alert_view",string='Commence')
    next_due_view = fields.Char(compute="_get_info_alert_view",string='Fini')
    warn_period_view = fields.Char(compute="_get_info_alert_view",string='Alerte en -')
    left_view = fields.Char(compute="_get_info_alert_view",string='Restant')
    
    state = fields.Selection([
                              ('draft','Normal'),
                              ('left', 'Dépassé'),
                              ('alert', 'Alerte'),
                              ('done', 'Validé')],
                             compute="_get_state", string='Etat',store=True)
    user_id = fields.Many2one('res.users','Opérateur')

