# -*- encoding: utf-8 -*-

from odoo import  api, models,fields,_
import odoo.addons.decimal_precision as dp


class ProductPricelistItem(models.Model):
    _inherit = 'product.pricelist.item'

    @api.one
    @api.depends('categ_id', 'product_tmpl_id', 'product_id', 'compute_price', 'fixed_price', \
        'pricelist_id', 'percent_price', 'price_discount', 'price_surcharge')
    def _get_pricelist_item_name_price(self):
        if self.template_id:
            self.name = _("%s") % (self.template_id.name)
        elif self.categ_id:
            self.name = _("Category: %s") % (self.categ_id.name)
        elif self.product_tmpl_id:
            self.name = self.product_tmpl_id.name
        elif self.product_id:
            self.name = self.product_id.display_name.replace('[%s]' % self.product_id.code, '')
            
        else:
            self.name = _("All Products")

        if self.compute_price == 'fixed':
            self.price = ("%s %s") % (self.fixed_price, self.pricelist_id.currency_id.name)
        elif self.compute_price == 'percentage':
            self.price = _("%s %% discount") % (self.percent_price)
        else:
            self.price = _("%s %% discount and %s surcharge") % (abs(self.price_discount), self.price_surcharge)

    @api.model
    def _get_default_pricelist(self):
        pricelists = self.env['product.pricelist'].search([])
        return pricelists and pricelists[0].id or False

    name = fields.Char(
        'Name', compute='_get_pricelist_item_name_price',
        help="Explicit rule name for this pricelist line.",store=True)
    template_id = fields.Many2one('product.pricelist.item.template','Modèle de tarif')
    unlimited_mileage = fields.Boolean('kilométrage illimité')
    vehicle_categ_id = fields.Many2one('fleet.vehicle.category','Catégorie de véhicle')
    days_min = fields.Float('Jour min')
    days_max = fields.Float('Jour max')
    kms_min = fields.Float('Km min')
    kms_max = fields.Float('Km max')
    forfait_days = fields.Float('Forfait Jour/Heure')
    forfait_kms = fields.Float('Forfait km')
    forfait_days_kms = fields.Float('Forfait km Jr/Hr Sup.')
    line_ids = fields.One2many('product.pricelist.item.productline','item_id','Lignes de prestation')
    pricelist_id = fields.Many2one('product.pricelist', 'Pricelist', index=True,default=_get_default_pricelist)
    


    
    @api.onchange('unlimited_mileage')
    def onchange_unlimited_mileage(self):
        if self.unlimited_mileage:
            self.kms_min = 0
            self.kms_max = 0

    @api.onchange('template_id')
    def on_change_template_id(self):
        template_read = self.template_id.read()
        data = {}
        if len(template_read) > 0:
            data = template_read[0]
            data['create_uid'] = False
            data['write_uid'] = False
            line_ids = []
            lines = self.env['product.pricelist.item.templateline'].browse(data['line_ids'])
            for line in lines:
                line_ids.append((0,0,{'product_id':line.product_id.id,'price_unit':line.price_unit}))
            data['line_ids'] = line_ids
        return {
            'value':data
        }

    @api.multi
    def name_get(self):
        
        context = dict(self.env.context)
        if not context.get('vehicle_categ_id'):
            return super(ProductPricelistItem,self).name_get()
        if not self.ids:
            return []
        res = []
        domain1 = [('id','in',self.ids),('vehicle_categ_id','=',context.get('vehicle_categ_id')),('days_min','<=',context.get('nombre_jour')),('days_max','>=',context.get('nombre_jour'))]
        domain2 = [('id','in',self.ids),('vehicle_categ_id','=',context.get('vehicle_categ_id')),('kms_min','<=',context.get('planned_odometer')),('kms_max','>=',context.get('planned_odometer'))]
        domain3 = [('id','in',self.ids),('vehicle_categ_id','=',context.get('vehicle_categ_id')),('unlimited_mileage','=',True)]
        
        
        item_ids1 = self.search(domain1).ids
        item_ids2 = self.search(domain2).ids
        item_ids3 = self.search(domain3).ids
        item_ids2.extend(item_ids3)
        item_ids = list(set(item_ids1).intersection(item_ids2))
        for item in self.browse(item_ids):
            name = item.name
            if not name:
                name = item.template_id.name
            if name:
                res.append((item.id, name))
        print(res)
        return res


class ProductPricelistItemProductline(models.Model):
    _name = 'product.pricelist.item.productline' 
    
  
    product_id = fields.Many2one('product.product','Prestation',domain=[('prestation_ok','=',True)])
    price_unit = fields.Float('Prix',digits= dp.get_precision('Product Price'))
    ttc = fields.Boolean('TTC')
    item_id = fields.Many2one('product.pricelist.item','Item')

class ProductPricelistItemTemplate(models.Model):
    _name = 'product.pricelist.item.template'

    name = fields.Char('Libellé')
    unlimited_mileage = fields.Boolean('kilométrage illimité')
    days_min = fields.Float('Jour min')
    days_max = fields.Float('Jour max')
    kms_min = fields.Float('Km min')
    kms_max = fields.Float('Km max')
    forfait_days = fields.Float('Forfait Jour/Heure')
    forfait_kms = fields.Float('Forfait km')
    forfait_days_kms = fields.Float('Forfait km Jr/Hr Sup.')
    line_ids = fields.One2many('product.pricelist.item.templateline','template_id','Lignes de prestation')

    @api.onchange('unlimited_mileage')
    def onchange_unlimited_mileage(self):
        if self.unlimited_mileage:
            self.kms_min = 0
            self.kms_max = 0

class ProductPricelistItemTemplateline(models.Model):
    _name = 'product.pricelist.item.templateline' 
    
  
    product_id = fields.Many2one('product.product','Prestation',domain=[('prestation_ok','=',True)])
    price_unit = fields.Float('Prix',digits= dp.get_precision('Product Price'))
    template_id = fields.Many2one('product.pricelist.item.template','Template')
    
    

class ProductPriceYield(models.Model):
    _name = 'product.price.yield'

    @api.model
    def _default_company_id(self):
        return self.env.user.company_id
    
    name = fields.Char('Libellé',required=True,default="/")
    company_id = fields.Many2one('res.company',string='Société',required=True,default=_default_company_id)
    agence_id = fields.Many2one('agence.agence',string='Agence')
    partner_id = fields.Many2one('res.partner','Client')
    company_type = fields.Selection(string='Type de client',
        selection=[('person', 'Individuel'), ('company', 'Société')])
    #sector_id = fields.Many2one('res.partner.sector','Secteur')
    category_id = fields.Many2one('fleet.vehicle.category','Catégorie')
    product_id = fields.Many2one('product.product','Prestation',domain="[('type','=','service')]")
    rate = fields.Float("Taux (%)" ,help="""Si 0 <= valeur <= 100 les tarifs seront augmentés de valeur/100.
                                            Si -100 <= valeur <= 0 les tarifs seront réduits de valeur/100.""")
    
    date_start = fields.Date('Date début')
    date_stop = fields.Date('Date fin')
    

    @api.model
    def create(self,vals):
        if vals.get('name', '/') == '/':
            vals['name'] = self.env['ir.sequence'].next_by_code('product.price.yield')
        return super(ProductPriceYield, self).create(vals)


    _sql_constraints = [
        ('name_uniq', 'unique(name)', "Code unique!"),
    ]
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
