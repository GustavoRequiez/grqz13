# Copyright 2018 Vauxoo (https://www.vauxoo.com) <info@vauxoo.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).
from odoo import fields, models


class SaleCommissionSetting(models.Model):
    _name = "sale.commission.setting"
    _rec_name = "day"

    day = fields.Integer('Days', required=True, help="Commission days")
    commission = fields.Float('Commission (%)', digits=(2, 4), required=True,
                              help="Commission value (%)")
