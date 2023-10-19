# -*- coding: utf-8 -*-
from datetime import timedelta
from odoo import models, fields, api,_
from odoo.exceptions import UserError

class FleetVehicleMoveTypeChoice(models.TransientModel):

    _name = 'fleet.vehicle.movetype.choice'

    
    
    
    @api.model
    def _get_default_contract_type_id(self):
        type_id = self.env['fleet.vehicle.contract.type'].search([('contract_cd', '=', True)])
        return type_id and type_id[0].id or False
    
    start_date = fields.Datetime('Départ le')
    interval = fields.Integer('Durée')
    move_type = fields.Selection([('cd','Contrat courte durée'),('ld','Contrat longue durée'),('or','OR')],'Type de mouvement',default='cd')
    vehicle_id = fields.Many2one("fleet.vehicle",'Parc')
    category_id = fields.Many2one("fleet.vehicle.category",'Catégorie')

    @api.multi
    def get_form(self):
        self.ensure_one()
        model = "fleet.vehicle.contract"
        contract_cd  =False
        c_type = self.env['fleet.vehicle.contract.type']
        
        auto_contract = auto_reservation = False
        if self.move_type == "or":
            form = self.env.ref('mro.mro_order_form_view')
            name = "Maintenance"
            model = "mro.order"            
        elif self.move_type == "ld":
            auto_contract = True
            form = self.env.ref('fleet.fleet_vehicle_contract_lld_form')
            name = "Contrat LLD"
            c_type = self.env['fleet.vehicle.contract.type'].search([('contract_cd', '=', contract_cd)])
        else:
            auto_reservation = True
            form = self.env.ref('fleet.fleet_vehicle_contract_form_planning')
            name = "Contrat LCD"
            contract_cd = True
            c_type = self.env['fleet.vehicle.contract.type'].search([('contract_cd', '=', contract_cd)])

        ctx = dict(self.env.context,
            default_model=model,
            default_vehicle_id = self.vehicle_id.id,
            default_category_id = self.category_id.id,
            default_contract_cd= contract_cd,
            default_type_id = c_type.id,
            default_lld_nombre_mois = self.interval, 
            default_nombre_jour = self.interval, 
            default_duration = self.interval, 
            default_date_start = self.start_date,
            default_start_date = self.start_date,
            auto_reservation = auto_reservation,
            auto_contract = auto_contract,
            confirm_mro = True,
            default_categ_id = self.env.ref('mro.product_category_mro').id  ##CECI A ÉTÉ AJOUTÉ POUR LE MRO
        )
        from_gantt = {  
            'name': _(name),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': model,
            'views': [(form.id, 'form')],
            'view_id': form.id,
            'nodestroy': True,
            'target' : 'new',
        }
        ctx.update({'from_gantt':from_gantt})
        return {
            'name': _(name),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': model,
            'views': [(form.id, 'form')],
            'view_id': form.id,
            'target' : 'new',
            'context': ctx,
        }

    @api.model
    def create(self, vals):
        return models.TransientModel.create(self, vals)
        
class FleetVehicleContractWizard(models.TransientModel):
    _name = "fleet.vehicle.contract.wizard"
    
    
    date_stop = fields.Date("Date de fin du contrat",required=True)
    date_start = fields.Date("Date de début de l'avenant",required=True)

    @api.onchange('date_stop')
    def onchange_date_stop(self):
        if self.date_stop:
            date_stop = fields.Date.from_string(self.date_stop)
            self.date_start = date_stop + timedelta(days=1)

    @api.onchange('date_start')
    def onchange_date_start(self):
        if self.date_start:
            date_start = fields.Date.from_string(self.date_start)
            self.date_stop = date_start + timedelta(days=-1)      
            
    @api.multi
    def create_contract(self):
        contract_obj = self.env['fleet.vehicle.contract']
        data= self
        contract = contract_obj.browse(self.env.context.get('active_id'))
        if contract.expiration_date < data.date_stop:
            raise UserError(_('La date de fin du contrat doit être < à la date du retour prévu.'))
        
        
        default = {
                   'state':'waiting',
                   'avenant':contract.avenant+1,
                   'contract_date_stop' :False,
                   'avenant_date_start' :False,
                   'contract_id':False,
                   'start_date':data.date_start,
                   }
        new = contract.copy(default=default)
        contract.write({'contract_date_stop':data.date_stop,
                                                            'avenant_date_start':data.date_start,
                                                            'contract_id':new.id})

        #contract_obj.get_update_cumulative(cr,uid,context.get('active_id')) ###Actualiser les cumuls
        if self.env.context.get('from_gantt'):
            from_gantt = dict(self.env.context.get('from_gantt'),res_id=contract.id)
            return from_gantt
        return True

class ContractVehicleChangeWizard(models.TransientModel):
    _name = "contract.vehicle.change.wizard"

    @api.model
    def _get_active_contract_id(self):
        return self.env.context.get('active_id')
    
    @api.model
    def _get_current_vehicle_id(self):
        contract = self.env['fleet.vehicle.contract'].browse(self.env.context.get('active_id'))
        return contract.vehicle_id.id

    @api.model
    def _get_expiration_date(self):
        contract = self.env['fleet.vehicle.contract'].browse(self.env.context.get('active_id'))
        return contract.expiration_date

    @api.one
    @api.depends('contract_id')
    def _get_prev_data(self):
        contract_odometer_obj =self.env['contract.vehicle.odometer']
        if self.contract_id.contract_vehicle_ids:
            domain = [('contract_id','=',self.env.context.get('active_id'))]
            line = self.env['contract.vehicle.odometer']
            lines = contract_odometer_obj.search(domain,order="id desc")
            if lines:
                line = lines[0]
            prev_vehicle_id = line.vehicle_id.id
            prev_odometer_start = line.odometer_start
            prev_start_date = line.start_date
            prev_src_agence_id = self.contract_id.src_agence_id.id
            prev_fuel_qty_start = line.fuel_qty_start
            prev_license_plate = line.vehicle_id.license_plate
            prev_category_id = line.vehicle_id.category_id.id
            prev_model_id = line.vehicle_id.model_id.id
        else:
            vehicle = self.contract_id.vehicle_id
            prev_vehicle_id = vehicle.id
            prev_odometer_start = self.contract_id.vehicle_odometer
            prev_start_date = self.contract_id.start_date
            prev_src_agence_id = self.contract_id.src_agence_id.id
            prev_fuel_qty_start = self.contract_id.fuel
            prev_license_plate = vehicle.license_plate
            prev_category_id = vehicle.category_id.id
            prev_model_id = vehicle.model_id.id

        self.prev_vehicle_id = prev_vehicle_id
        self.prev_odometer_start = prev_odometer_start
        self.prev_start_date = prev_start_date
        self.prev_src_agence_id = prev_src_agence_id
        self.prev_fuel_qty_start = prev_fuel_qty_start
        self.prev_license_plate = prev_license_plate
        self.prev_category_id = prev_category_id
        self.prev_model_id = prev_model_id

    @api.one
    @api.depends('vehicle_id')
    def _get_prev_data2(self):
        self.license_plate = self.vehicle_id.license_plate
        self.category_id = self.vehicle_id.category_id.id
        self.model_id = self.vehicle_id.model_id.id
        
    
    contract_id = fields.Many2one('fleet.vehicle.contract','Contrat',default=_get_active_contract_id)
    
    prev_vehicle_id = fields.Many2one("fleet.vehicle",'Matériel',required=True,compute="_get_prev_data")
    prev_license_plate = fields.Char("Immatriculation",compute="_get_prev_data")
    prev_category_id = fields.Many2one("fleet.vehicle.category","Catégorie",compute="_get_prev_data")
    prev_model_id = fields.Many2one("fleet.vehicle.model","Modèle",compute="_get_prev_data")
    prev_odometer_start = fields.Float('Compteur départ',compute="_get_prev_data")
    prev_odometer_stop = fields.Float('Compteur retour')
    prev_start_date = fields.Datetime('Date départ',compute="_get_prev_data")
    prev_expiration_date = fields.Datetime('Date retour')
    prev_src_agence_id  = fields.Many2one('agence.agence','Agence départ',compute="_get_prev_data")
    prev_dest_agence_id  = fields.Many2one('agence.agence','Agence retour')
    prev_fuel_qty_start = fields.Integer('Carburant départ',compute="_get_prev_data")
    prev_fuel_qty_stop = fields.Integer('Carburant retour')
    
    
    vehicle_id = fields.Many2one("fleet.vehicle",'Matériel',required=True)
    license_plate = fields.Char("Immatriculation",compute="_get_prev_data2")
    category_id = fields.Many2one("fleet.vehicle.category","Catégorie",compute="_get_prev_data2")
    model_id = fields.Many2one("fleet.vehicle.model","Modèle",compute="_get_prev_data2")
    odometer_start = fields.Float('Compteur départ')
    start_date = fields.Datetime('Date départ',required=True)
    expiration_date = fields.Datetime('Retour prévu le',required=True,default=_get_expiration_date)
    src_agence_id  = fields.Many2one('agence.agence','Agence départ')
    dest_agence_id  = fields.Many2one('agence.agence','Agence retour')
    fuel_qty_start = fields.Integer('Carburant départ')


    
    @api.onchange('vehicle_id')
    def onchange_vehicle_id(self):
        self.odometer_start = self.vehicle_id.odometer
        
    @api.onchange('prev_vehicle_id')
    def onchange_prev_vehicle_id(self):
        self.prev_odometer_stop = self.prev_vehicle_id.odometer
        self.prev_dest_agence_id = self.contract_id.dest_agence_id.id
        


    @api.onchange('prev_src_agence_id','prev_dest_agence_id')
    def onchange_prev_agence_id(self):
        self.src_agence_id = self.prev_src_agence_id.id
        self.dest_agence_id = self.prev_dest_agence_id.id
    
    @api.onchange('prev_expiration_date')
    def onchange_expiration_date(self):
        self.start_date = self.prev_expiration_date

    @api.multi
    def modify_contract(self):
        ### AJOUTER UNE LIGNE POUR LE RELAIS , METTRE FIN AU MOUVEMENT EN COURS DU CONTRAT
        ### ET CRÉER UN NOUVEAU MOUVEMENT POUR LE NUVEAU MATÉRIEL
        contract_obj = self.env['fleet.vehicle.contract']
        contract_odometer_obj =self.env['contract.vehicle.odometer']

        data= self
        
        contract = contract_obj.browse(self.env.context.get('active_id'))
        if data.prev_expiration_date > contract.expiration_date:
            raise UserError(_("""La date de retour du matériel doit être comprise dans 
                                l'interval de validité du contrat."""))
        if contract.contract_vehicle_ids: 
        ### S'IL EXISTE DÉJÀ DES CHANGEMENTS , MODFIER LE DERNIER CHANGEMENT 
        ### AVEC LES DONNÉES DU RETOUR
            write_data = {
                     "contract_id" : self.env.context.get('active_id'),
                     "vehicle_id":data.prev_vehicle_id.id,
                     "odometer_stop" : data.prev_odometer_stop,
                     'expiration_date': data.prev_expiration_date,
                     "fuel_qty_stop" : data.prev_fuel_qty_stop,
                     }
            domain = [('contract_id','=',write_data['contract_id']),('vehicle_id','=',write_data['vehicle_id'])]
            line = contract_odometer_obj.search(domain,order="id desc")
            line[0].write(write_data)
        else:
            ### SINON ON CRÉÉ LA LIGNE POUR LE MATRÉIEL D'ORIGINE DU CONTRAT 
            ### L'OPTION SPÉCIAL PERMET DE DISTINGUER LE MATERIEL D'ORIGINE S 
            ### DES MATÉRIELS DE RELAIS.
            line1 = {
                     "contract_id" : self.env.context.get('active_id'),
                     "vehicle_id":data.prev_vehicle_id.id,
                     "odometer_start" : contract.vehicle_odometer,
                     "odometer_stop" : data.prev_odometer_stop,
                     "fuel_qty_start" : contract.fuel,
                     "fuel_qty_stop" : data.prev_fuel_qty_stop,
                     "start_date": contract.start_date,
                     "expiration_date": data.prev_expiration_date,
                     "special":True
                     }
            contract_odometer_obj.create(line1)
            
        line2 = {
                 "contract_id" : self.env.context.get('active_id'),
                 "vehicle_id":data.vehicle_id.id,
                 "odometer_start" : data.odometer_start,
                 "fuel_qty_start" : data.fuel_qty_start,
                 'start_date': data.start_date,
                 'expiration_date': data.expiration_date,
                 }

        ### AJOUTER LA LIGNE POUR LE MATÉIRLE DE RELAIS.
        contract_odometer_obj.create(line2)
        
        prev_move = contract.vehicle_position_id
        
        contract.write({'vehicle_id':data.vehicle_id.id})
        
        context = dict(self.env.context)

        context.update({"prev_write_data":{
                                      'odometer_end' : data.prev_odometer_stop,
                                      'date_stop' : data.prev_expiration_date,
                                      'fuel_qty_end' : data.prev_fuel_qty_stop,
                                      'dest_agence_id' : data.prev_dest_agence_id.id
                                      }})
        self.env.context = context
        contract_obj.create_move(contract,prev_move,data.odometer_start,data.start_date,contract.expiration_date)
        if self.env.context.get('from_gantt'):
            from_gantt = dict(self.env.context.get('from_gantt'),res_id=contract.id)
            return from_gantt
        return True

    @api.multi
    def modify_contract_lld(self):
        ### AJOUTER UNE LIGNE POUR LE RELAIS , METTRE FIN AU MOUVEMENT EN COURS DU CONTRAT
        ### ET CRÉER UN NOUVEAU MOUVEMENT POUR LE NUVEAU MATÉRIEL
        contract_obj = self.env['fleet.vehicle.contract']
        contract_odometer_obj =self.env['contract.vehicle.odometer']

        data= self
        
        contract = contract_obj.browse(self.env.context.get('active_id'))
        if data.prev_expiration_date > contract.expiration_date:
            raise UserError(_("""La date de retour du matériel doit être comprise dans 
                                l'interval de validité du contrat."""))
        if contract.contract_vehicle_ids: 
        ### S'IL EXISTE DÉJÀ DES CHANGEMENTS , MODFIER LE DERNIER CHANGEMENT 
        ### AVEC LES DONNÉES DU RETOUR
            write_data = {
                     "contract_id" : self.env.context.get('active_id'),
                     "vehicle_id":data.prev_vehicle_id.id,
                     "odometer_stop" : data.prev_odometer_stop,
                     'expiration_date': data.prev_expiration_date,
                     "fuel_qty_stop" : data.prev_fuel_qty_stop,
                     }
            domain = [('contract_id','=',write_data['contract_id']),('vehicle_id','=',write_data['vehicle_id'])]
            line = contract_odometer_obj.search(domain,order="id desc")
            line[0].write(write_data)
        else:
            ### SINON ON CRÉÉ LA LIGNE POUR LE MATRÉIEL D'ORIGINE DU CONTRAT 
            ### L'OPTION SPÉCIAL PERMET DE DISTINGUER LE MATERIEL D'ORIGINE S 
            ### DES MATÉRIELS DE RELAIS.
            line1 = {
                     "contract_id" : self.env.context.get('active_id'),
                     "vehicle_id":data.prev_vehicle_id.id,
                     "odometer_start" : contract.vehicle_odometer,
                     "odometer_stop" : data.prev_odometer_stop,
                     "fuel_qty_start" : contract.fuel,
                     "fuel_qty_stop" : data.prev_fuel_qty_stop,
                     "start_date": contract.start_date,
                     "expiration_date": data.prev_expiration_date,
                     "special":True
                     }
            contract_odometer_obj.create(line1)
            
        line2 = {
                 "contract_id" : self.env.context.get('active_id'),
                 "vehicle_id":data.vehicle_id.id,
                 "odometer_start" : data.odometer_start,
                 "fuel_qty_start" : data.fuel_qty_start,
                 'start_date': data.start_date,
                 'expiration_date': data.expiration_date,
                 }

        ### AJOUTER LA LIGNE POUR LE MATÉIRLE DE RELAIS.
        contract_odometer_obj.create(line2)
        
        prev_move = contract.vehicle_position_id

        move = contract_obj.create_move(contract,prev_move,data.odometer_start,data.start_date,contract.expiration_date)
        if not contract.contract_cd:
            move_data_lld = {
                        'vehicle_id':data.vehicle_id.id,
                        'odometer_start' :  data.odometer_start,
                        'odometer_end' :data.odometer_start,
                        'date_start':data.start_date,
                        'date_stop':data.expiration_date
                        }
            move.write(move_data_lld)
        if self.env.context.get('from_gantt'):
            from_gantt = dict(self.env.context.get('from_gantt'),res_id=contract.id)
            return from_gantt
        return True
    
class ContractVehicleOdometer(models.Model):
    _name = "contract.vehicle.odometer"

    contract_id = fields.Many2one('fleet.vehicle.contract','Contrat',required=True,ondelete="cascade")
    vehicle_id = fields.Many2one("fleet.vehicle",'Matériel',required=True)
    odometer_start = fields.Float('Compteur départ')
    odometer_stop = fields.Float('Compteur retour')
    fuel_qty_start = fields.Integer('Carburant départ')
    fuel_qty_stop = fields.Integer('Carburant retour')
    odometer_variation = fields.Float(compute="_get_odometer_variation",string="Cons. km")
    fuel_variation = fields.Integer(compute="_get_fuel_variation",string="Cons. carburant")
    start_date = fields.Datetime("Date départ",required=True)
    expiration_date = fields.Datetime("Date retour")
    special = fields.Boolean("Principal",readonly=True)
    
    @api.one
    def _get_odometer_variation(self):
        diff = self.odometer_stop - self.odometer_start
        self.odometer_variation = 0
        if diff > 0:
            self.odometer_variation = diff

    @api.one
    def _get_fuel_variation(self):
        diff = self.fuel_qty_start - self.fuel_qty_stop
        self.fuel_variation = diff