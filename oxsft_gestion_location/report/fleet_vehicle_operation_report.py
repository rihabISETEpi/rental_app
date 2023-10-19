# -*- coding: utf-8 -*-


from odoo import models, fields, api


class FleetVehicleOperationReport(models.Model):
    _name = "fleet.vehicle.operation.report"
    
    exclure = fields.Boolean('Exclu')
    nature = fields.Selection([('fr','Fournisseur (Relations)'),('clt','Client (Relations)')],'Nature')
    type = fields.Selection([('invoice','Facture,Avoir'),('order','Commande')],'Type')
    s_type = fields.Selection([('standard','Standard'),('autre','Autre')],'S/Type')
    statut = fields.Selection([('en_cours','En cours'),('attente','Effectué'),('invoice','Facturé')],'Statut')
    libelle_operation = fields.Char('Libellé opération')
    mro_id = fields.Many2one('mro.order','Code opération')
    date = fields.Datetime('Date')
    odometer = fields.Float('Compteur')
    odometer2 = fields.Float('Compteur 2')
    fr_quantity = fields.Float('Qté')
    clt_quantity = fields.Float('Qté clt')
    fr_ht = fields.Float('HT Fourni.')
    clt_ht = fields.Float('HT Client')
    numero_accord = fields.Char('N° accord')
    partner_id = fields.Many2one('res.partner','Nom du tiers')
    invoice_id = fields.Many2one("account.invoice","N° facture")
    date_facture = fields.Date(related='invoice_id.date_invoice',string='Facture du')
    vehicle_id = fields.Many2one('fleet.vehicle','N° parc',ondelete="cascade")
    parts_line_id = fields.Many2one('mro.order.parts.line','Ligne mro',ondelete="cascade")
    purchase_line_id = fields.Many2one('purchase.order.line','Ligne commande',ondelete="cascade")
    invoice_line_id = fields.Many2one('account.invoice.line','Ligne facture',ondelete="cascade")
            
    @api.model_cr
    def init(self):
        
        self.env.cr.execute("""select mro_id from account_invoice where mro_id is not null 
                    union select mro_id from purchase_order where mro_id is not null
                    union select id from mro_order where state<>'done'""")
        res = self.env.cr.fetchall()
        mro_ids = []
        
        for line in res:
            mro_ids.append(line[0])
        
        
        
        self.env.cr.execute("""delete from fleet_vehicle_operation_report""")
        self.env.cr.execute("""
            INSERT INTO fleet_vehicle_operation_report(id,nature,type,s_type,statut,
                             libelle_operation,mro_id,date,odometer,odometer2,fr_quantity,clt_quantity,
                             fr_ht,clt_ht,numero_accord,partner_id,invoice_id,
                             vehicle_id,purchase_line_id,invoice_line_id) 
               select ROW_NUMBER() OVER (ORDER BY vehicle_id ASC) as id,* from(
                select cast('fr' as varchar) as nature,cast('invoice' as varchar) as type, cast('standard' as varchar) as s_type,cast('invoice' as varchar) as statut,
                name as libelle_operation,
                (select mro_id from account_invoice where id=invoice_id) as mro_id,
                (select mo2.date_start from mro_order mo2 where mo2.id=(select mro_id from account_invoice where id=invoice_id)) as date,
                (select mo3.km_start from mro_order mo3 where mo3.id=(select mro_id from account_invoice where id=invoice_id)) as odometer,
                0 as odometer2,quantity as fr_quantity, 0 as clt_quantity, quantity*price_unit as fr_ht, 0 as clt_ht,
                (select po1.name from purchase_order po1 where po1.id=(select pol1.order_id from purchase_order_line pol1 where pol1.id=ail1.purchase_line_id)) as numero_accord,
                (select partner_id from account_invoice ai1 where ai1.id=ail1.invoice_id) as partner_id,
                ail1.invoice_id as invoice_id,
                (select vehicle_id from account_invoice ai4 where ai4.id=ail1.invoice_id) as vehicle_id,
                purchase_line_id as purchase_line_id,
                id as invoice_line_id
                from account_invoice_line ail1 where (select type from account_invoice where id=invoice_id)='in_invoice'  and 
                ((select historique from product_product where id=product_id) is true) and
                (select vehicle_id from account_invoice ai4 where ai4.id=ail1.invoice_id) is not null
                union
                select cast('fr' as varchar) as nature,cast('invoice' as varchar) as type, cast('standard' as varchar) as s_type,cast('invoice' as varchar) as statut,
                name as libelle_operation,
                (select mro_id from account_invoice where id=invoice_id) as mro_id,
                (select mo2.date_start from mro_order mo2 where mo2.id=(select mro_id from account_invoice where id=invoice_id)) as date,
                (select mo3.km_start from mro_order mo3 where mo3.id=(select mro_id from account_invoice where id=invoice_id)) as odometer,
                0 as odometer2,quantity as fr_quantity, 0 as clt_quantity, -quantity*price_unit as fr_ht, 0 as clt_ht,
                (select po1.name from purchase_order po1 where po1.id=(select pol1.order_id from purchase_order_line pol1 where pol1.id=ail1.purchase_line_id)) as numero_accord,
                (select partner_id from account_invoice ai1 where ai1.id=ail1.invoice_id) as partner_id,
                ail1.invoice_id as invoice_id,
                (select vehicle_id from account_invoice ai4 where ai4.id=ail1.invoice_id) as vehicle_id,
                purchase_line_id as purchase_line_id,
                id as invoice_line_id
                from account_invoice_line ail1 where (select type from account_invoice where id=invoice_id)='in_refund' and
                ((select historique from product_product where id=product_id) is true)
                and (select vehicle_id from account_invoice ai4 where ai4.id=ail1.invoice_id) is not null
                
                union
                select cast('clt' as varchar) as nature,cast('invoice' as varchar) as type, cast('standard' as varchar) as s_type,cast('invoice' as varchar) as statut,
                name as libelle_operation,
                (select mro_id from account_invoice where id=invoice_id) as mro_id,
                (select mo2.date_start from mro_order mo2 where mo2.id=(select mro_id from account_invoice where id=invoice_id)) as date,
                (select mo3.km_start from mro_order mo3 where mo3.id=(select mro_id from account_invoice where id=invoice_id)) as odometer,
                0 as odometer2,0 as fr_quantity, quantity as clt_quantity, 0 as fr_ht, quantity*price_unit as clt_ht,
                (select po1.name from purchase_order po1 where po1.id=(select pol1.order_id from purchase_order_line pol1 where pol1.id=ail1.purchase_line_id)) as numero_accord,
                (select partner_id from account_invoice ai1 where ai1.id=ail1.invoice_id) as partner_id,
                ail1.invoice_id as invoice_id,
                (select vehicle_id from account_invoice ai4 where ai4.id=ail1.invoice_id) as vehicle_id,
                purchase_line_id as purchase_line_id,
                id as invoice_line_id
                from account_invoice_line ail1 where (select type from account_invoice where id=invoice_id)='out_invoice' and
                ((select historique from product_product where id=product_id) is true)
                and (select vehicle_id from account_invoice ai4 where ai4.id=ail1.invoice_id) is not null
                union
                select cast('clt' as varchar) as nature,cast('invoice' as varchar) as type, cast('standard' as varchar) as s_type,cast('invoice' as varchar) as statut,
                name as libelle_operation,
                (select mro_id from account_invoice where id=invoice_id) as mro_id,
                (select mo2.date_start from mro_order mo2 where mo2.id=(select mro_id from account_invoice where id=invoice_id)) as date,
                (select mo3.km_start from mro_order mo3 where mo3.id=(select mro_id from account_invoice where id=invoice_id)) as odometer,
                0 as odometer2,0 as fr_quantity, quantity as clt_quantity, 0 as fr_ht, -quantity*price_unit as clt_ht,
                (select po1.name from purchase_order po1 where po1.id=(select pol1.order_id from purchase_order_line pol1 where pol1.id=ail1.purchase_line_id)) as numero_accord,
                (select partner_id from account_invoice ai1 where ai1.id=ail1.invoice_id) as partner_id,
                ail1.invoice_id as invoice_id,
                (select vehicle_id from account_invoice ai4 where ai4.id=ail1.invoice_id) as vehicle_id,
                purchase_line_id as purchase_line_id,
                id as invoice_line_id
                from account_invoice_line ail1 where (select type from account_invoice where id=invoice_id)='out_refund' and
                ((select historique from product_product where id=product_id) is true)
                and (select vehicle_id from account_invoice ai4 where ai4.id=ail1.invoice_id) is not null

                union
                select cast('fr' as varchar) as nature,cast('order' as varchar) as type, cast('standard' as varchar) as s_type,cast('en_cours' as varchar) as statut,
                name as libelle_operation,
                (select mro_id from purchase_order where id=pol.order_id) as mro_id,
                (select mo2.date_start from mro_order mo2 where mo2.id=(select mro_id from purchase_order where id=pol.order_id)) as date,
                (select mo3.km_start from mro_order mo3 where mo3.id=(select mro_id from purchase_order where id=pol.order_id)) as odometer,
                0 as odometer2,product_qty as fr_quantity, 0 as clt_quantity, product_qty*price_unit as fr_ht, 0 as clt_ht,
                (select name from purchase_order where id=(select order_id from purchase_order_line where id=pol.id)) as numero_accord,
                (select partner_id from purchase_order where id=pol.order_id) as partner_id,
                null as numero_facture,
                (select vehicle_id from purchase_order where id=pol.order_id) as vehicle_id,
                id as purchase_line_id,
                null as invoice_line_id
                from purchase_order_line pol where (select vehicle_id from purchase_order po where po.id=pol.order_id) is not null
                and ((select historique from product_product where id=product_id) is true)
                and pol.id not in (select purchase_line_id from account_invoice_line where purchase_line_id is not null)
                ) as union_result""")
        
        self.env.cr.execute("select max(id) from fleet_vehicle_operation_report")
        
        res = self.env.cr.fetchall()
        max_id = 0
        for l in res:
            if l[0] is not None:
                max_id = l[0]
        self.env.cr.execute("ALTER SEQUENCE fleet_vehicle_operation_report_id_seq RESTART WITH %s",(max_id+1,))
        print(mro_ids,tuple(mro_ids),max_id+1)





