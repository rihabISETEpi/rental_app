# -*- encoding: utf-8 -*-
##############################################################################
#
#    ODOO, Open Source Management Solution
#    Copyright (c) 2017 OXYSOFT (afilali@oxysoft.fr).
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

{
    'name': 'Gestion des locations',
    'version': '2.0.1',
    'category': 'Management',
    'website' : '',
    'author': 'OXYSOFT',
    'depends': ["fleet","hr","stock","sale","purchase",
                "account_cancel","product","base_geolocalize","base_vat",
                "mro",'nxtm_web_gantt','nxtm_l10n_fr_rib',
                'nxtm_l10n_fr_zipcode','account_payment_partner'],
    'data': [
             'static/src/css/style.xml',
             'security/security.xml',
             'security/ir.model.access.csv',
             'wizard/tms_gmao_pm_alert_process_view.xml',
             'wizard/purchase_order_wizard_view.xml',
             'wizard/account_invoice_wizard_view.xml',
             'wizard/account_invoice_wizard_view2.xml',
             'wizard/fleet_vehicle_contract_wizard_view.xml',
             'data/location_data.xml',
             'data/product_data.xml',
             'data/module_data.xml',
             'views/pricelist_view.xml',
             'views/gmao_view.xml',
             'views/fleet_view.xml',
             'views/fleet_vehicle_contract_view.xml',
             'views/hr_view.xml',
             'views/checklist_view.xml',
             'views/template_view.xml',
             'views/product_view.xml',
             'views/mro_view.xml',
             'views/res_partner_view.xml',
             'views/account_invoice_view.xml',
             'views/account_period8_view.xml',
             'views/account_payment_view.xml',
             'views/sale_view.xml',
             'views/purchase_view.xml',
             'views/stock_view.xml',
             'views/report_invoice.xml',
             'views/report_contract.xml',
             'views/webclient_templates.xml',
             'actions/module_actions.xml',
             'menus/module_menus.xml',
             'sequences/module_sequences.xml',
             'report.xml',
             'data/module_view.xml',
    ],
    'application': True,
    'installable': True,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
