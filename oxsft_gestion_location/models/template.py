# -*- coding: utf-8 -*-

from odoo import models, fields

#from gmao import UNITE_SELECTION ++ zart

UNITE_SELECTION = [
                   ('annee','Année'),('mois','Mois'),
                   ('days', 'Jours'),('horaire','Heure'),
                   ('km', 'Km')
                  ]
class FleetVehicleFiltreTemplate(models.Model):
    _name = 'fleet.vehicle.filtre.template'
    
    name = fields.Integer('Intervalle',required=True)
    meter = fields.Selection([("j","h")], 'Unité', required=True)
    line_ids = fields.One2many("fleet.line.reparation","template_id","Reparations")
    checklist_ids1 = fields.One2many('fleet.line.checklist','template_id','Niveau',domain=[('name.code', '=', 'niveau')])
    checklist_ids2 = fields.One2many('fleet.line.checklist','template_id','Graissage',domain=[('name.code', '=', 'graissage')])
    checklist_ids3 = fields.One2many('fleet.line.checklist','template_id','Pression',domain=[('name.code', '=', 'pression')])
    checklist_ids4 = fields.One2many('fleet.line.checklist','template_id','Remplacement huile',domain=[('name.code', '=', 'huile')])
    checklist_ids5 = fields.One2many('fleet.line.checklist','template_id','Autres entretiens',domain=[('name.code', '=', 'autres')])
    model_id =fields.Many2one("fleet.vehicle.model","Modèle",ondelete='restrict',required=True)

class FleetVehicleFiltre(models.Model):
    _name = 'fleet.vehicle.filtre'
    
    
    name = fields.Integer('Intervalle',required=True)
    meter = fields.Selection(UNITE_SELECTION, 'Unité', required=True)
    line_ids = fields.One2many("fleet.line.reparation","filtre_id","Reparations")
    checklist_ids1 = fields.One2many('fleet.line.checklist','filtre_id','Niveau',domain=[('name.code', '=', 'niveau')])
    checklist_ids2 = fields.One2many('fleet.line.checklist','filtre_id','Graissage',domain=[('name.code', '=', 'graissage')])
    checklist_ids3 = fields.One2many('fleet.line.checklist','filtre_id','Pression',domain=[('name.code', '=', 'pression')])
    checklist_ids4 = fields.One2many('fleet.line.checklist','filtre_id','Remplacement huile',domain=[('name.code', '=', 'huile')])
    checklist_ids5 = fields.One2many('fleet.line.checklist','filtre_id','Autres entretiens',domain=[('name.code', '=', 'autres')])
    vehicle_id = fields.Many2one("fleet.vehicle","Véhicule",ondelete='cascade',required=True)
    model_id = fields.Many2one("fleet.vehicle.model","Modèle")

class FleetLineReparation(models.Model):

    _name = 'fleet.line.reparation'
    
    product_id = fields.Many2one('product.product','Référence',ondelete='restrict',required=True)
    description = fields.Text('Description')
    product_qty = fields.Float("Quantité",required=True,default=1)
    log_services_id = fields.Many2one("fleet.vehicle.log.services","Service")
    template_id = fields.Many2one('fleet.vehicle.filtre.template',"Template")
    filtre_id = fields.Many2one('fleet.vehicle.filtre',"Filtre")
    pm_model_id = fields.Many2one('tms.gmao.pm.model',"Modèle d'alerte")
    pm_model_template_id = fields.Many2one('tms.gmao.pm.model.template',"Template modèle d'alerte")
    pm_id = fields.Many2one('tms.gmao.pm','Maintenance programmée')



