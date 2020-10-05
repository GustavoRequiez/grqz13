{
    'name': 'Import Customer Invoices from XML',
    'summary': 'Create multiple Invoices from XML in other systems',
    'version': '13.0.1.0.0',
    'category': 'Localization/Mexico',
    'author': 'Vauxoo',
    'website': 'https://www.vauxoo.com',
    'depends': [
        'l10n_mx_edi_vendor_bills',
    ],
    'license': 'LGPL-3',
    'data': [
        'data/account_data.xml',
        'data/partner_tags.xml',
        'views/assets.xml',
        'views/account_invoice_view.xml',
        'wizards/attach_xmls_wizard_view.xml',
    ],
    'installable': True,
}
