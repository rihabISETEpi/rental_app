# -*- coding: utf-8 -*-

from odoo import models,fields


class HrEmployee(models.Model):
    _inherit="hr.employee"

    driver_ok = fields.Boolean('Chauffeur', help="Cochez cette case pour définir l'employé comme chauffeur pour la gestion de voyages")
    
