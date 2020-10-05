# -*- coding: utf-8 -*-
# pylint: disable=manifest-required-author
# Copyright 2017 Humanytek.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': "Sale Order Observation",
    'author': "Humanytek",
    'website': "http://www.humanytek.com",
    'category': 'Sale',
    'version': '12.0.1.0.0',
    'depends': [
        'mrp_sale_info'
    ],
    'data': [
        'views/sale_view.xml',
        'views/mrp_view.xml',
        'views/account_invoice_view.xml',
        'views/stock_move_view.xml',
        'report/sale_report_template.xml',
        'report/deliveryslip_report.xml',
        'report/invoice_report_template.xml',
        'security/ir.model.access.csv',
    ],
}
