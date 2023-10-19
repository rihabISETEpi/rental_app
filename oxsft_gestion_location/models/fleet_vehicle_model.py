# -*- coding: utf-8 -*-

from odoo import models,api,fields



class FleetVehicleModel(models.Model):
    _inherit = 'fleet.vehicle.model'

    @api.model_cr
    def init(self):
        models = self.search([])
        for model in models:
            if not model.product_id:
                product_data = {'name' : model.name, 'type':'product','sale_ok':False,'purchase_ok':False}
                product = self.env['product.product'].create(product_data)
                model.product_id = product.id

    @api.multi
    @api.depends('name', 'brand_id','code')
    def name_get(self):
        res = []
        for record in self:
            name = record.name
            if record.brand_id.name:
                name = record.brand_id.name + '/' + name
            if record.code:
                name = "[" + record.code + "]" + name
            res.append((record.id, name))
        return res

    image = fields.Binary("Logo", attachment=True,
        help="This field holds the image used as logo for the brand, limited to 1024x1024px.")
    image_medium = fields.Binary("Medium-sized image", attachment=True,
        help="Medium-sized logo of the brand. It is automatically "
             "resized as a 128x128px image, with aspect ratio preserved. "
             "Use this field in form views or some kanban views.")
    image_small = fields.Binary("Small-sized image", attachment=True,
        help="Small-sized logo of the brand. It is automatically "
             "resized as a 64x64px image, with aspect ratio preserved. "
             "Use this field anywhere a small image is required.")
    pmm_ids =  fields.One2many('tms.gmao.pm.model', 'model_id', 'Modèles d’alertes')
    product_id  =  fields.Many2one('product.product', 'Article')
    code = fields.Char(string="Code modèle")
    brand_id = fields.Many2one('fleet.vehicle.model.brand', 'Marque (D.1) :', required=False,help='Brand of the vehicle')
    type_id = fields.Many2one('fleet.vehicle.type', 'Type,famille :')
    category_id = fields.Many2one('fleet.vehicle.category', 'Sous type,catégorie :')
    ss_type_id = fields.Many2one('fleet.vehicle.model.ss.type', 'SS type :')
    nature = fields.Many2one('fleet.vehicle.model.nature', 'Nature du modèle :')
    nature_cpt = fields.Many2one('fleet.vehicle.model.compteur', 'Nature du compteur :')
    nature_cpt2 = fields.Many2one('fleet.vehicle.model.compteur', 'Nature du 2ième compteur :')
    nature_jauge = fields.Many2one('fleet.vehicle.model.jauge', 'Nature de la jauge :')
    notes =fields.Text('Description détaillée :')
    stock = fields.Boolean("Gestion du modèle en stock")
    mouvement = fields.Boolean("Pris en compte dans les mouvements")
    capacite_reservoir =  fields.Float('Capacité réservoir :')
    capacite_reservoir2 = fields.Float('Capacité réservoir 2 :')
    cons_urbaine = fields.Float('Urbaine :')
    cons_mixte = fields.Float('Mixte 90 km/h :')
    cons_extra_urbaine =fields.Float('Extra urbaine 120 km/h :')
    t01 = fields.Char('Type mine (D.2.1) :')
    t02 = fields.Char('Hauteur utile :')
    t03 = fields.Char('PTAC (F.2) :')
    t04 = fields.Char('Denom. Com. mine (D.3) :')
    t10 = fields.Many2one('fleet.vehicle.model.genre', 'Genre (J.1) :')
        
    t11 = fields.Char('Puissance fiscale (P.6):')
    t12 = fields.Char('Hauteur hors tout :')
    t13 = fields.Char('PTRA (F.3) :')
    t14 = fields.Char('Charge maxi tech (F.1) :')
    t20 = fields.Many2one('fleet.vehicle.model.carrosserie', 'Carrosserie (J.3) :')

    t21 = fields.Char('Puissance DIN (P.2) :')
    t22 = fields.Char('Surface :')
    t23 = fields.Char('Charge utile :')
    t24 = fields.Char('Masse en service (G) :')
    t30 = fields.Many2one('fleet.vehicle.model.energie', 'Energie (P.3) :')

    t31 = fields.Char('Longueur utile :')
    t32 = fields.Char('Volume :')
    t33 = fields.Char('PV (G.1) :')
    t34 = fields.Char('Catégorie (J) :')

    t41 = fields.Char('Longueur hors tout :')
    t42 = fields.Char('Nb places assises (S.1) :')
    t43 = fields.Char('Bruit (U.1) :')
    t44 = fields.Char('Carrosserie CE (J.2) :')

    t51 = fields.Char('Largeur utile :')
    t52 = fields.Char('Nb places debout (S.2) :')
    t53 = fields.Char('Régime moteur (U.2) :')
    t54 = fields.Char('CO2 (V.7) :')

    t61 = fields.Char('Largeur hors tout :')
    t62 = fields.Char('Nb portes :')
    t63 = fields.Char('Type variante (D.2) :')
    t64 = fields.Char('Classe env. (v.9) :')

    pneumatique = fields.Char('Pneumatiques :')
    cylindre = fields.Char('Cylindrée (P.1) :')

    # garantie
    garantie_id = fields.Many2one('fleet.vehicle.model.garantie', 'Garantie :')
    nb_mois = fields.Float('Nb de mois :')
    cpteur_maxi = fields.Float('Cpteur maxi :')
    cpteur_maxi2 = fields.Float('Cpteur 2 maxi :')
        
    # caractéristiques
        
    caracteristique_ids = fields.One2many('fleet.vehicle.model.caracteristique', 'model_id', 'Caractéristiques')
    equipement_ids = fields.One2many('fleet.vehicle.model.equipement', 'model_id', 'Équipements')
    
    # onglet Divers
    d_libelle = fields.Char('Libellé :')
    d_code1 = fields.Char('Code CODEX :')
    d_code2 = fields.Char('Code EAN :')

    d_famille_p_id = fields.Many2one('fleet.vehicle.famille', 'Primaire :')
    d_famille_s_id = fields.Many2one('fleet.vehicle.famille', "Secondaire :")
    d_famille_t_id = fields.Many2one('fleet.vehicle.famille', "Tertiaire :")


    def update_all_vehicle(self):
        model_ids = self.ids
        self.env['fleet.vehicle'].create_pm_and_link(model_ids)
        return True

    @api.onchange('garantie_id')
    def onchange_garantie_id(self):
        if self.garantie_id:
            self.nb_mois = self.garantie_id.nb_mois
            self.cpteur_maxi = self.garantie_id.cpteur_maxi
            self.cpteur_maxi2 = self.garantie_id.cpteur_maxi2

    @api.model
    def create(self, vals):
        product_data = {'name' : vals.get('name'), 'type':'product','sale_ok':False,'purchase_ok':False}
        product = self.env['product.product'].create(product_data)
        vals['product_id'] = product.id
        return super(FleetVehicleModel, self).create(vals)


    @api.onchange('brand_id')
    def _onchange_brand(self):
        print("nothing")

class FleetVehicleModelCaracteristique(models.Model):
    _name = 'fleet.vehicle.model.caracteristique'

    name = fields.Char('Caractéristiques')
    pere = fields.Char('Père')
    tech = fields.Char('Tech')
    ok = fields.Boolean('Oui')
    code1 = fields.Char('Libellé code')
    code2 = fields.Char('Code')
    valeur1 = fields.Char('Libellé valeur')
    valeur2 = fields.Integer('Valeur')
    date1 = fields.Char('Libellé date')
    date2 = fields.Date('Date')
    model_id = fields.Many2one('fleet.vehicle.model', 'Modèle')
    vehicle_id = fields.Many2one('fleet.vehicle', 'Véhicule')


class FleetVehicleModelEquipement(models.Model):
    _name = 'fleet.vehicle.model.equipement'

    name = fields.Many2one('fleet.vehicle.model.equipement.equipement', 'Équipements')
    pere = fields.Char('Père')
    tech = fields.Char('Tech')
    ok = fields.Boolean('Oui')
    code1 = fields.Char('Libellé code')
    code2 = fields.Char('Code')
    valeur1 = fields.Char('Libellé valeur')
    valeur2 = fields.Integer('Valeur')
    date1 = fields.Char('Libellé date')
    date2 = fields.Date('Date')
    model_id = fields.Many2one('fleet.vehicle.model', 'Modèle')
    vehicle_id = fields.Many2one('fleet.vehicle', 'Véhicule')


class FleetVehicleModelEquipementEquipement(models.Model):
    _name = 'fleet.vehicle.model.equipement.equipement'
    
    name = fields.Char('Libellé')

    
class FleetVehicleModelGenre(models.Model):
    _name = 'fleet.vehicle.model.genre'

    name = fields.Char('Nom', required=True)
 
 
class FleetVehicleModelCarrosserie(models.Model):
    _name = 'fleet.vehicle.model.carrosserie'

    name = fields.Char('Nom', required=True)

class FleetVehicleModelEnergie(models.Model):
    _name = 'fleet.vehicle.model.energie'

    name = fields.Char('Nom', required=True)

class FleetVehicleModelGarantie(models.Model):
    _name = 'fleet.vehicle.model.garantie'

    code = fields.Char('Code', required=True)
    name =fields.Char('Libelle:', required=True)
    nb_mois = fields.Float('Nb de mois:')
    cpteur_maxi = fields.Float('Cpteur maxi:')
    cpteur_maxi2 = fields.Float('Cpteur 2 maxi:')


class FleetVehicleModelSsType(models.Model):
    _name = 'fleet.vehicle.model.ss.type'
    
    code = fields.Char('Code', required=True)
    name = fields.Char('Nom', required=True)

class FleetVehicleModelNature(models.Model):
    _name = 'fleet.vehicle.model.nature'

    code = fields.Char('Code', required=True)
    name = fields.Char('Nom', required=True)

class FleetVehicleModelCompteur(models.Model):
    _name = 'fleet.vehicle.model.compteur'

    code = fields.Char('Code', required=True)
    name = fields.Char('Nom', required=True)
    
    _sql_constraints = [
        ('code_uniq', 'unique(code)', "Le code doit être unique !")
    ]
class FleetVehicleModelCompteur2(models.Model):
    _name = 'fleet.vehicle.model.compteur2'

    code = fields.Char('Code', required=True)
    name = fields.Char('Nom', required=True)

class FleetVehicleModelJauge(models.Model):
    _name = 'fleet.vehicle.model.jauge'

    code = fields.Char('Code', required=True)
    name = fields.Char('Nom', required=True)
    

class FleetVehicleType(models.Model):
    """Type de véhicule"""
    _name = 'fleet.vehicle.type'
    
    name = fields.Char('Nom type', required=True)


    _sql_constraints = [
        ('name_uniq', 'unique(name)', "Le nom du type de matériel doit être unique !")
    ]

class FleetVehicleFamille(models.Model):
    _name = 'fleet.vehicle.famille'

    name = fields.Char('Nom', required=True)

    _sql_constraints = [
        ('name_uniq', 'unique(name)', "Le nom de la famille doit être unique !")
    ]
    
class FleetVehicleCategory(models.Model):
    """Catégorie de véhicule"""
    _name = 'fleet.vehicle.category'

    @api.model
    def _vehicle_nature_get(self):
        nature_obj = self.env['fleet.vehicle.nature']

        result = []
        natures = nature_obj.search([])
        for nature in natures:
            result.append((nature.code, nature.name))
        return result

    nature_materiel = fields.Selection(_vehicle_nature_get, 'Nature du matériel :',default="vehicle_ok",change_default=True)
    name = fields.Char('Nom', required=True)
    hook_ok = fields.Boolean('Peut être accroché')
    vehicle_ids = fields.One2many('fleet.vehicle', 'category_id', string='Véhicules', domain=[('nature_materiel', '=', 'vehicle_ok')], ondelete="set null")
    trailer_ids = fields.One2many('fleet.vehicle', 'category_id', string='Remorques', domain=[('nature_materiel', '=', 'trailer_ok')], ondelete="set null")
    note = fields.Text('Description')

    _sql_constraints = [
        ('fleet_vehicle_category_name_uniq', 'unique(name)', 'Le nom de catégorie doit être unique !')
    ]
