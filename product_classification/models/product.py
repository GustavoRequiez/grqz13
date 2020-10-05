# -*- coding: utf-8 -*-

from odoo import fields, models, api, exceptions


class ProductClassification(models.Model):
    _inherit = 'product.template'
    _name = 'product.template'

    its_line = fields.Boolean(string="Its Line")
    classification_ABC = fields.Selection([
        ('A', 'A'),
        ('B', 'B'),
        ('C', 'C'),
        ('O', 'O')], string="Classification ABC")
    classification_XYZ = fields.Selection([
        ('X', 'X'),
        ('Y', 'Y'),
        ('Z', 'Z')], string="Classification XYZ")
