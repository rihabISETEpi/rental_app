# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from odoo import models, fields


class FleetLineChecklist(models.Model):

    _name = 'fleet.line.checklist'

    name = fields.Many2one('fleet.verification','Vérification')
    log_services_id = fields.Many2one("fleet.vehicle.log.services","Service")
    template_id = fields.Many2one('fleet.vehicle.filtre.template',"Template")
    filtre_id = fields.Many2one('fleet.vehicle.filtre',"Filtre")


class FleetVerification(models.Model):

    _name = 'fleet.verification'

    code = fields.Selection([('niveau','Niveau'),('graissage','Graissage'),('pression','Pression'),('huile','Remplacement huile'),('autres','Autres entretiens')],"Code")
    name = fields.Char('Nom de la vérification')


class FleetVerificationType(models.Model):

    _name = 'fleet.verification.type'
    
    code = fields.Integer("Code")
    name = fields.Char('Nom')



