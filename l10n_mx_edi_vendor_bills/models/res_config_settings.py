# Copyright 2020, Vauxoo, S.A. de C.V.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_mx_edi_fuel_code_sat_ids = fields.Many2many(
        'l10n_mx_edi.product.sat.code', 'SAT fuel codes', readonly=False,
        related='company_id.l10n_mx_edi_fuel_code_sat_ids')
