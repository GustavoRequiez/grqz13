# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Master Production Schedule',
    'version': '1.0',
    'category': 'Manufacturing',
    'sequence': 50,
    'summary': 'Master Production Schedule',
    'depends': ['mrp', 'purchase'],
    'description': """
Master Production Schedule
==========================

Sometimes you need to create the purchase orders for the components of
manufacturing orders that will only be created later.  Or for production orders
where you will only have the sales orders later.  The solution is to predict
your sale forecasts and based on that you will already create some production
orders or purchase orders.

You need to choose the products you want to add to the report.  You can choose
the period for the report: day, week, month, ...  It is also possible to define
safety stock, min/max to supply and to manually override the amount you will
procure.
""",
    'data': [
        'views/mrp_mps_report_views.xml',
        'report/mrp_mps_report_templates.xml',
    ],
    'demo': [
    ],
    'qweb': ['static/src/xml/mps_backend.xml'],
    'application': False,
    'license': 'OEEL-1',
}
