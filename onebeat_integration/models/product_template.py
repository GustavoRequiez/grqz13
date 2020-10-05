# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.tools.float_utils import float_round


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    buffer_size = fields.Float(
    )
