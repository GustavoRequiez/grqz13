# -*- coding: utf-8 -*-
# Copyright 2018 Vauxoo (https://www.vauxoo.com) <info@vauxoo.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

{
    'name': "incoming_products_kardex",
    'summary': """
        Incoming Products Kardex""",
    'description': """
        Module to create Incoming Products Kardex from a purchase order.
    """,
    'author': "gflores",
    'website': "https://www.gruporequiez.com",
    'category': 'Inventory',
    'version': '12.0.0.0.1',
    'license': "LGPL-3",
    'depends': [
        'product',
        'stock',
        'purchase'
    ],
    'data': [
        # data
        'data/report_data.xml',
        # views
        'views/incoming_products_kardex.xml',
        # Reports
        'report/product_kardex_report_definition.xml',
        'report/product_kardex_report_templates.xml',

    ],
    'demo': [
    ],
    'installable': True,
}
