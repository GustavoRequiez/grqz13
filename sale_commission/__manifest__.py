# Copyright 2018 Vauxoo (https://www.vauxoo.com) <info@vauxoo.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

{
    'name': "Salesman Commission",
    'summary': """
    """,
    'author': "Vauxoo",
    'website': "https://www.vauxoo.com",
    'category': 'Sale',
    'version': '12.0.1.0.2',
    'license': "LGPL-3",
    'depends': [
        'account',
        'sale',
        'sale_brand',
        'sales_team',
    ],
    'data': [
        # Security
        'security/ir.model.access.csv',
        # Data
        # Views
        'views/sale_commission_views.xml',
        'views/sale_commission_settings_views.xml',
        'views/sale_commission_brand_views.xml',
        # Reports
        'report/sale_commission_report_definition.xml',
        'report/sale_commission_report_templates.xml',
    ],
    'demo': [
    ],
    'installable': True,
}
