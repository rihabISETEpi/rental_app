# -*- coding: utf-8 -*-

from datetime import timedelta
import time

from odoo import api, _, fields, models
from odoo.exceptions import UserError
from odoo.http import request


STATE_SELECTION = [
        ('draft', 'DRAFT'),
        ('released', 'WAITING PARTS'),
        ('ready', 'READY TO MAINTENANCE'),
        ('done', 'DONE'),
        ('cancel', 'CANCELED')
    ]


def searchkey(obj, key):
    """Does BFS on JSON-like object `obj` to find a dict with a key == to `key` and 
    returns the associated value.  Returns None if it didn't find `key`."""
    queue = [obj]
    while queue:
        item = queue.pop(0)
        if type(item) is list:
            queue.extend(item)
        elif type(item) is dict:
            for k in item:
                if k == key:
                    return item[k]
                else:
                    queue.append(item[k])
    return None



class MroOrder(models.Model):
    """
    Maintenance Orders
    """
    _inherit = 'mro.order'
    _order = "date_start desc"

    MAINTENANCE_TYPE_SELECTION1 = [
        ('bm', 'Breakdown'),
        ('cm', 'Corrective'),
        ('pm', u'Programmée'),
    ]
    @api.multi
    def action_view_purchase(self):
        mod_obj = self.env['ir.model.data']
        act_obj = self.env['ir.actions.act_window']

        result = act_obj.for_xml_id('purchase', 'purchase_action')
        #compute the number of invoices to display
        po_ids = []
        for mro in self:
            po_ids += [purchase.id for purchase in mro.purchase_ids]
        #choose the view_mode accordingly
        if len(po_ids)>1:
            result['domain'] = "[('id','in',["+','.join(map(str, po_ids))+"])]"
        else:
            res = mod_obj.get_object_reference('purchase', 'purchase_order_form')
            result['views'] = [(res and res[1] or False, 'form')]
            result['res_id'] = po_ids and po_ids[0] or False
        return result

    @api.multi
    def action_view_invoice(self):
        '''
        This function returns an action that display existing invoices of given sales order ids. It can either be a in a list or in a form view, if there is only one invoice to show.
        '''
        mod_obj = self.env['ir.model.data']
        act_obj = self.env['ir.actions.act_window']

        result = act_obj.for_xml_id('account', 'action_invoice_tree1')
        #compute the number of invoices to display
        inv_ids = []
        for mro in self:
            inv_ids += [invoice.id for invoice in mro.customer_invoice_ids if invoice.type=='out_invoice']
        #choose the view_mode accordingly
        if len(inv_ids)>1:
            result['domain'] = "[('id','in',["+','.join(map(str, inv_ids))+"])]"
        else:
            res = mod_obj.get_object_reference('account', 'invoice_form')
            result['views'] = [(res and res[1] or False, 'form')]
            result['res_id'] = inv_ids and inv_ids[0] or False
        return result
    
    @api.one
    @api.depends('purchase_ids')
    def _purchase_exists(self):
        purchase_exists = False
        if self.purchase_ids:
            purchase_exists = True
        self.purchase_exists = purchase_exists

    @api.one
    @api.depends('customer_invoice_ids')
    def _invoice_exists(self):
        invoice_exists = False
        if self.customer_invoice_ids:
            invoice_exists = True
        self.invoice_exists = invoice_exists

    @api.model
    def _default_location_source(self):
        dummy,location_id  = self.env['ir.model.data'].get_object_reference("stock","stock_location_stock")
        if location_id:
            return location_id
        return False

    @api.model
    def _default_asset_id(self):
        asset = self.env['asset.asset'].search([])
        asset_id = False
        if asset:
            asset_id = asset[0].id
        else:
            asset_id = self.env['asset.asset'].create({'name':'Asset système'})
        return asset_id


    asset_id = fields.Many2one('asset.asset', 'Asset', required=False, readonly=True, states={'draft': [('readonly', False)]},default=_default_asset_id)
    
    vehicle_id = fields.Many2one('fleet.vehicle', 'Véhicule', readonly=True, states={'draft': [('readonly', False)]})
    km_start = fields.Float('Km')
    maintenancier_id = fields.Many2one('hr.employee', 'Maintenancier', help="Employé qui effectue la maintenance", readonly=True, states={'draft': [('readonly', False)]})
    user_id = fields.Many2one('res.users', 'Responsable', readonly=True,default=lambda self: self.env.user.id)
    maintenance_type = fields.Selection(MAINTENANCE_TYPE_SELECTION1, 'Type de maintenance', required=True, readonly=True, states={'draft': [('readonly', False)]})
    description = fields.Char('Description', size=64, translate=True, required=False, readonly=True, states={'draft': [('readonly', False)]})
    service_type_id = fields.Many2one('fleet.service.type', "Type d'intervention", domain=[('mro_ok','=',True)], readonly=True, states={'draft': [('readonly', False)]})
    cost_id = fields.Many2one('fleet.vehicle.cost', invisible=True, readonly=True)
    alert_id = fields.Many2one('tms.gmao.pm.alert', 'Alerte',domain="[('vehicle_id','=',vehicle_id),('state_process','=','progress')]")
    operation_ids = fields.One2many('mro.order.operation', 'mro_id', 'Opérations')
    parts_location_id =fields.Many2one('stock.location', 'Source',default=_default_location_source)
    parts_lines = fields.One2many('mro.order.parts.line', 'maintenance_id', 'Planned parts',readonly=False)
       
    purchase_ids = fields.One2many('purchase.order','mro_id','Achats')
    customer_invoice_ids = fields.One2many('account.invoice','mro_id','Facture client')
    purchase_exists = fields.Boolean(compute="_purchase_exists",string='Achats liés?',store=True)
    invoice_exists = fields.Boolean(compute="_invoice_exists",string='Factures liées?',store=True)
        
    vehicle_position_id = fields.Many2one('fleet.vehicle.move','Position')
    date_start = fields.Datetime('Date début',required=True,default=fields.Datetime.now)
    duration = fields.Float('Durée en jour')
    date_stop = fields.Datetime('Date fin')
    
    assistance = fields.Boolean('Assistance',default=False)
    address = fields.Text(u"Adresse de prise en charge")
    latitude = fields.Float(string='Latitude', digits=(16, 5))
    longitude = fields.Float(string='Longitude', digits=(16, 5))
    date_localization = fields.Date(string='Date de localisation')


    @api.multi
    def open_map(self):
        for order in self:
            url="http://maps.google.com/maps?oi=map&q="
            if order.address:
                url+=order.address
            else:
                raise UserError(_("Aucune adresse n'est saisie"))
        return {'type': 'ir.actions.act_url','target': 'new','url':url}

    @api.multi
    def open_map2(self):
        google_maps_api_key = self.env['ir.config_parameter'].sudo().get_param('google_maps_api_key')
        try:
            import googlemaps
            gmaps = googlemaps.Client(key=google_maps_api_key)
        except ValueError as e:
            raise UserError(_("Aucune clé google maps n'est configurée"))
        for order in self:
            lat = order.latitude
            lng = order.longitude
            reverse_geocode_result = gmaps.reverse_geocode((lat, lng))
            add  = ""
            if reverse_geocode_result:
                add = reverse_geocode_result[0]['formatted_address']
            url="http://maps.google.com/maps?oi=map&q="
            url +=add
        return {'type': 'ir.actions.act_url','target': 'new','url':url}
    
    @api.multi
    def open_map3(self):
        for order in self:
            url="http://maps.google.com/maps?oi=map&q="
            if order.address:
                url+=""
        return {'type': 'ir.actions.act_url','target': 'new','url':url}
    
    @api.multi
    def _check_date_stop(self) :
        for mro in self:
            if mro.date_stop < mro.date_start:
                return False
        return True

    
    _constraints = [(_check_date_stop,"Erreur : 'Date fin' doit être > à 'Date début'!", ['date_stop'])]

    @api.multi
    def unlink(self):
        for mro in self:
            if mro.state in ('ready','done'):
                raise UserError(_("Vous devez d'abord annuler."))
        return super(MroOrder,self).unlink()

    @api.onchange('duration','date_start')
    def onchange_data_date_stop(self):
        if self.date_start:
            interval = timedelta(days=self.duration)
            self.date_stop = fields.Datetime.from_string(self.date_start) + interval
    

    def create_move(self):
        move = self.env["fleet.vehicle.move"]
        order = self
        if order.vehicle_id.last_move_id.name.code in ("LOC","RESA"):
            #mves = self.env["fleet.vehicle.move"].search([("vehicle_id",'=',order.vehicle_id.id),('name.code','not in',("LOC","RESA")),"|","&",("date_start","<=",order.date_start),("date_stop",">=",order.date_start),"&",("date_start","<=",order.date_stop),("date_stop",">=",order.date_stop)])
            #if not mves:
            self.env.context = dict(self.env.context, disponibility_check_ok=True)
        model, dispo_move_name_id = self.env['ir.model.data'].get_object_reference('fleet', 'fleet_vehicle_move_location0')
        model, model_id = self.env['ir.model.data'].get_object_reference('fleet', 'fleet_vehicle_move_location2')
        if model_id:
            model, or_model_id = self.env['ir.model.data'].get_object_reference('fleet', 'fleet_vehicle_move_type_en')
            data = {
                        "name" :model_id,'date_start':order.date_start,
                        'date_stop':order.date_stop,'odometer_start':order.km_start,
                        'vehicle_id':order.vehicle_id.id,'mro_id':order.id,
                        'doc_type_id' : or_model_id,
                        }
                
            prev_move = order.vehicle_position_id
            prev_move_name_id = prev_move.name.id
            if prev_move_name_id != model_id:###SI CE N'EST PAS UN MOUVEMENT DE LOCATION
                move = self.env['fleet.vehicle.move'].create(data)
                order.vehicle_position_id = move.id
                if dispo_move_name_id == prev_move_name_id:### S'IL S'AGIT D'UN MOUVEMENT DE DISPONIBILITÉ
                    ###LES MOUVEMENT DE DISPONIBILITÉ ONT ÉTÉ CRÉÉS POUR AFFICHER LE MATERIEL DANS LE PLANNING
                    ###POUR LES MATÉRIELS N'AYANT AUCUN MOUVEMENT.DÈS LORS QU'ON CRÉÉ UN NOUVEAU MOUVEMENT , ON SUPPRIME
                    ###LE MOUVEMENT DE DISPONIBILITÉ
                    prev_move.unlink()
                else:
                    prev_move.action_done()
            else: ### ON FAIT JUSTE UNE MISE À JOUR AU CAS OÙ LES DATES AURAIENT ÉTÉ CHANGÉES
                prev_move.write(data)
        else:
            raise UserError(_(u'Erreur emplacement arrivé.'))
        
        return move
            
    def action_ready(self):
        result = super(MroOrder,self).action_ready()
        for order in self:
            order.create_move()
        return result

    def action_confirm(self):        
        procurement_obj = self.env['procurement.order']
        for order in self:
            proc_ids = []
            group_id = self.env['procurement.group'].create({'name': order.name,'vehicle_id':order.vehicle_id.id})
            for line in order.parts_lines:
                vals = {
                    'name': order.name,
                    'origin': order.name,
                    'company_id': order.company_id.id,
                    'group_id': group_id.id,
                    'date_planned': order.date_planned,
                    'product_id': line.parts_id.id,
                    'product_qty': line.parts_qty,
                    'product_uom': line.parts_uom.id,
                    'location_id': order.asset_id.property_stock_asset.id,
                    }
                proc_id = procurement_obj.create(vals)
                proc_ids.append(proc_id)
            procurement_obj.run(proc_ids)
            order.write({'state':'released','procurement_group_id':group_id.id})
            
            order.create_move()
            
            if order.alert_id.state_process == 'progress':
                order.alert_id.validate_alert(order.alert_id.periodic, order.date_start, order.km_start)
        
            
            ####BUG MRO CONSOMMABLE
        
        return 0

    def action_done(self):
        for order in self:
            order.parts_move_lines.action_done()
            date_stop = self.date_stop
            if not order.date_stop:
                date_stop = time.strftime('%Y-%m-%d %H:%M:%S')
            order.write({"date_stop":date_stop})
            if order.alert_id.state_process == 'progress':
                order.alert_id.validate_alert(order.alert_id.id,order.alert_id.periodic, order.date_start, order.km_start)
        
            line_obj = self.env['fleet.vehicle.operation.report']
            if not(order.purchase_ids or order.customer_invoice_ids):
                for line in order.parts_lines:
                    line_obj.search([('parts_line_id','=',line.id),('parts_line_id','!=',False)]).unlink()
                    data_achat = {
                         'nature' : 'fr',
                         's_type' : 'standard',
                         'statut' : 'attente',
                         'libelle_operation' : line.name,
                         'mro_id' : line.maintenance_id.id,
                         'date' : line.maintenance_id.date_start,
                         'odometer' : line.maintenance_id.km_start,
                         'fr_quantity' :line.parts_qty,
                         'fr_ht' : line.parts_qty*line.price_unit,
                         'partner_id' : line.supplier_id.id,
                         'vehicle_id' : line.maintenance_id.vehicle_id.id,
                         'parts_line_id' :line.id,
                         }
                    data_vente = {
                         'nature' : 'clt',
                         's_type' : 'standard',
                         'statut' : 'attente',
                         'libelle_operation' : line.name,
                         'mro_id' : line.maintenance_id.id,
                         'date' : line.maintenance_id.date_start,
                         'odometer' : line.maintenance_id.km_start,
                         'clt_quantity' :line.parts_qty,
                         'clt_ht' : line.parts_qty*line.price_unit2,
                         'partner_id' : line.partner_id.id,
                         'vehicle_id' : line.maintenance_id.vehicle_id.id,
                         'parts_line_id' :line.id,
                         }
                    if line.parts_id.historique:###SI L'ARTICLE EST PRÉVU POUR ÊTRE AJOUTÉ DANS L'HISTORIQUE
                        line_obj.create(data_achat)
                        line_obj.create(data_vente)
        self.write({'state': 'done', 'date_execution': time.strftime('%Y-%m-%d %H:%M:%S')})
        return True
    
    @api.model
    def create(self, vals): ###ir.sequence new
        if vals.get('name','/')=='/':
            if vals.get("assistance"):
                vals['name'] = self.env['ir.sequence'].next_by_code('mro.order.assistance') or '/'
            else:
                vals['name'] = self.env['ir.sequence'].next_by_code('mro.order') or '/'
        mro = models.Model.create(self, vals)
        self.env['fleet.vehicle.odometer'].create({'vehicle_id':mro.vehicle_id.id,'value':vals.get('km_start'),'date':mro.date_start,'origin':'mro'})
        if self.env.context.get('confirm_mro'):
            #workflow.trg_validate(self._uid, "mro.order", mro.id, "button_confirm_order", self._cr)
            self.env['mro.order'].browse(mro.id).button_confirm_order() #++zart
        return mro

    @api.multi
    def write(self, vals):
        result = models.Model.write(self, vals)
        for mro in self:
            self.env.context = dict(self.env.context, disponibility_check_ok=False)
            print(mro.vehicle_id.last_move_id.name.code)
            if mro.vehicle_id.last_move_id.name.code in ("LOC","RESA"):
                #mves = self.env["fleet.vehicle.move"].search([("vehicle_id",'=',mro.vehicle_id.id),('name.code','not in',("LOC","RESA")),"|","&",("date_start","<=",mro.date_start),("date_stop",">=",mro.date_start),"&",("date_start","<=",mro.date_stop),("date_stop",">=",mro.date_stop)])
                #print "mves",mves and mves[0].name.code
                #if not mves:
                self.env.context = dict(self.env.context, disponibility_check_ok=True)
                
            if vals.get('km_start'):
                self.env['fleet.vehicle.odometer'].create({'vehicle_id':mro.vehicle_id.id,'value':vals.get('km_start'),'date':mro.date_start,'origin':'mro'})
            if vals.get('date_stop') or vals.get('date_start') or vals.get('km_start'):
                if mro.vehicle_position_id.mro_id.id == mro.id and mro.vehicle_position_id.state == 'draft':
                    mro.vehicle_position_id.write({'date_start':mro.date_start,'date_stop':mro.date_stop,'odometer_start':mro.km_start})
        return result

    @api.onchange('vehicle_id')
    def onchange_vehicle_id(self):
        self.km_start = self.vehicle_id.odometer
        self.vehicle_position_id = self.vehicle_id.last_move_id.id

    @api.onchange('alert_id')
    def onchange_alert_id(self):
        parts_ids = self.env['mro.order.parts.line'].search([('maintenance_id','=',self.id)])
        for parts in parts_ids:
            parts.unlink()
        parts_lines=[]
        alert = self.alert_id
        for line in alert.pm_id.line_ids:
            parts_lines.append([0,False,{'parts_id':line.product_id.id,'parts_qty':line.product_qty,'parts_uom':line.product_id.uom_id.id,'name':line.product_id.name,'price_unit':line.product_id.standard_price,'price_unit2':line.product_id.lst_price,'product_qty_available':line.product_id.qty_available}])
            
        self.parts_lines =  parts_lines
    
    @api.onchange('maintenance_type')
    def onchange_maintenance_type(self):
        if self.maintenance_type:
            service_types = self.env['fleet.service.type'].search([('maintenance_type','=',self.maintenance_type)])
            if len(service_types)==1:
                self.service_type_id = service_types[0].id



class MroOrderOperation(models.Model):
    _name="mro.order.operation"
    _description="Opérations de maintenance"

    mro_id = fields.Many2one('mro.order', "mro id")
    employee_id = fields.Many2one('hr.employee', "Travailleur", required=True)
    hours = fields.Float("Nombre d'heures", required=True)
    description = fields.Text('Description')

class MroRequest(models.Model):
    """
    Maintenance Requests
    """
    _inherit = 'mro.request'

    def action_confirm(self):
        order = self.env['mro.order']
        order_id = False
        for request in self:
            order_id = order.create({
                'date_planned':request.requested_date,
                'date_scheduled':request.requested_date,
                'date_execution':request.requested_date,
                'origin': request.name,
                'state': 'draft',
                'maintenance_type': 'bm',
                'asset_id': request.asset_id.id,
                'vehicle_id': request.vehicle_id.id,
                'description': request.cause,
                'problem_description': request.description,
            })
        self.write({'state': 'run'})
        return order_id.id

    vehicle_id = fields.Many2one('fleet.vehicle', 'Véhicule')
    asset_id = fields.Many2one('asset.asset', 'Asset', required=False, readonly=True, states={'draft': [('readonly', False)]})


class MroOrderPartsLine(models.Model):
    _inherit = 'mro.order.parts.line'
    
    @api.one
    @api.depends('parts_qty','price_unit','price_unit2')
    def _get_all_amount(self):
        self.amount_total = self.parts_qty * self.price_unit
        self.amount_total2 = self.parts_qty * self.price_unit2

    @api.one
    @api.depends('parts_id')
    def _get_qty_available(self):
        self.product_qty_available = self.parts_id.qty_available
    
    parts_id = fields.Many2one('product.product', 'Produit', required=True)
    product_qty_available = fields.Float(compute="_get_qty_available",string='Quantité en stock')
    price_unit = fields.Float("Prix d'achat")
    price_unit2 = fields.Float("Prix de vente")
        
    amount_total = fields.Float(compute="_get_all_amount",string='HT Frs',store=True)
    amount_total2 = fields.Float(compute="_get_all_amount",string='HT Clts',store=True)
        
    state = fields.Selection(STATE_SELECTION,related='maintenance_id.state',string="Statut",default="draft")
    maintenance_id = fields.Many2one('mro.order', 'Maintenance Order',ondelete="cascade")
    to_invoice = fields.Boolean("À facturer")
    partner_id = fields.Many2one('res.partner','Client',domain=[('customer','=',True)])
    supplier_id = fields.Many2one('res.partner','Fournisseur',domain=[('supplier','=',True)])


    @api.onchange('parts_id')
    def onchange_parts(self):
        res = super(MroOrderPartsLine,self).onchange_parts()
        self.name = self.parts_id.name
        self.product_qty_available = self.parts_id.qty_available
        self.price_unit = self.parts_id.standard_price
        self.price_unit2 = self.parts_id.lst_price
        return res

    @api.multi
    def write(self, vals):
        result  =super(MroOrderPartsLine,self).write(vals)
        line_obj = self.env['fleet.vehicle.operation.report']
        for parts_line in self: 
            fr_line = line_obj.search([('parts_line_id','=',parts_line.id),('parts_line_id','!=',False),('nature','=','fr')])
            clt_line = line_obj.search([('parts_line_id','=',parts_line.id),('parts_line_id','!=',False),('nature','=','clt')])
            data_fr = {
                         'fr_quantity' :parts_line.parts_qty,
                         'fr_ht' : parts_line.parts_qty*parts_line.price_unit,
                         'partner_id' : parts_line.supplier_id.id,
                    }
            data_clt = {
                         'clt_quantity' :parts_line.parts_qty,
                         'clt_ht' : parts_line.parts_qty*parts_line.price_unit2,
                         'partner_id' : parts_line.partner_id.id,
                    }    
            fr_line.write(data_fr)  
            clt_line.write(data_clt) 
        return result

