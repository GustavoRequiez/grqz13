# Copyright 2018 Vauxoo (https://www.vauxoo.com) <info@vauxoo.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).
from odoo import fields, models


class SaleCommissionBrand(models.Model):
    _name = "sale.commission.brand"
    _rec_name = "user_id"

    user_id = fields.Many2one('res.users', 'Salesman', required=True,
                              help="Salesman")
    brand_id = fields.Many2one('product.brand', 'Brand', required=True,
                               help="Brand")
    commission = fields.Float('Commission (%)', required=True,
                              help="Commission (%)")
