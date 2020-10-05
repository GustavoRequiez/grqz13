# Copyright 2017 Humanytek.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ProductCompromise(models.Model):
    _name = "product.compromise"

    qty_compromise = fields.Float('Compromise quantity')
    stock_move_in_id = fields.Many2one('stock.move', 'Incoming products')
    stock_move_out_id = fields.Many2one('stock.move', 'Outgoing products')
    state = fields.Selection(
        related='stock_move_in_id.state',
        readonly=True,
        store=False)
    product_id = fields.Many2one(
        related='stock_move_in_id.product_id',
        string='Product',
        readonly=True,
        store=False)
    move_picking_id = fields.Many2one(
        related='stock_move_in_id.picking_id',
        string='',
        readonly=True,
        store=False)

    _sql_constraints = [
        ('stock_move_uniq',
         'UNIQUE (stock_move_in_id, stock_move_out_id)',
         'the relationship must be unique!')]
