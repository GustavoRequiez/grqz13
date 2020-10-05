# Copyright 2020, Vauxoo, S.A. de C.V.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_mx_edi_fuel_code_sat_ids = fields.Many2many(
        'l10n_mx_edi.product.sat.code', string='SAT fuel codes',
        domain=[('applies_to', '=', 'product')])
