# Copyright 2017 Humanytek.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    product_default_code = fields.Char(
        related='product_id.default_code',
        string='Default Code',
        readonly=True,
        store=False)
    product_brand = fields.Char(
        related='product_id.product_brand_id.name',
        string='Brand',
        readonly=True,
        store=False)
    product_categ = fields.Char(
        related='product_id.categ_id.name',
        string='Category',
        readonly=True,
        store=False)
    mrp_id = fields.Many2one(
        'mrp.production',
        compute='_compute_mrp_info',
        string='MRP Production',
        readonly=True,
        store=False)
    mrp_move_raw_ids = fields.One2many(
        related='mrp_id.move_raw_ids',
        string='Moves',
        readonly=True,
        store=False)

    def _compute_mrp_info(self):
        mrp = self.env['mrp.production']
        lines = self.search([
            ('product_id', 'in', self.mapped('product_id.id')),
            ('order_id', 'in', self.mapped('order_id.id'))],
            order='product_id')
        assigned_mrp_ids = []
        for line in lines:
            line.mrp_id = mrp.search([
                ('id', 'not in', assigned_mrp_ids),
                ('sale_id', '=', line.order_id.id),
                ('product_id', '=', line.product_id.id),
                ('state', '!=', 'cancel'),
                ('product_qty', '=', line.product_uom_qty)],
                order='id', limit=1)
            # Ignores current MRP order in case multiple lines has the
            # same product quantity for the same product into the same SO
            assigned_mrp_ids.append(line.mrp_id.id)
