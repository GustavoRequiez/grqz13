# -*- coding: utf-8 -*-
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

{
    'name': "revenue_history_projection",
    'summary': """
        Revenue history projection""",
    'description': """
        Revenue history projection
    """,
    'author': "gflores",
    'website': "https://www.gruporequiez.com",
    'category': 'Account',
    'version': '12.0.0.0.1',
    'license': "LGPL-3",
    'depends': [
        'account',
        'account_accountant',
    ],
    'data': [
        # data
        # views
        'views/revenue_history_projection_view.xml',
        # Reports

    ],
    'demo': [
    ],
    'installable': True,
}
