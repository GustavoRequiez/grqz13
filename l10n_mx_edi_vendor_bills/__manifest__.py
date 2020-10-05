# Copyright 2017, Jarsa Sistemas, S.A. de C.V.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

{
    'name': 'Import Supplier Invoice from XML',
    'summary': 'Create multiple Invoices from XML',
    'version': '13.0.1.0.1',
    'category': 'Localization/Mexico',
    'author': 'Vauxoo,Jarsa',
    'website': 'https://www.vauxoo.com',
    'depends': [
        'l10n_mx_edi',
    ],
    'license': 'LGPL-3',
    'data': [
        'security/groups.xml',
        'views/assets.xml',
        'views/account_invoice_view.xml',
        'wizards/attach_xmls_wizard_view.xml',
        'views/res_config_settings_views.xml',
    ],
    'demo': [
        'demo/ir_attachment.xml',
    ],
    'qweb': [
        'static/src/xml/*.xml',
    ],
    'installable': True,
}
