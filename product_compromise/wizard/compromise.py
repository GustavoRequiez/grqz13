# Copyright 2017 Humanytek.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
_logger = logging.getLogger(__name__)


class Compromise(models.TransientModel):
    _name = "compromise"

    qty_compromise = fields.Float('Compromise quantity', required=True)
    stock_move_in_id = fields.Many2one(
        'stock.move',
        'Incoming products',
        domain=lambda self: [
            ('product_id.id', '=', self._context.get('product_id')),
            ('picking_type_id.code', '=', 'incoming'),
            ('state', '=', 'assigned'),
            ('location_dest_id.id', '=', self._context.get('location_id'))],
        required=True)
    stock_move_out_id = fields.Many2one(
        'stock.move',
        'Outgoing products',
        default=lambda self: self._context.get('move_out'),
        required=True)
    compromise_max = fields.Float('Max quantity', readonly=True)

    # @api.multi
    @api.onchange('stock_move_in_id')
    def onchange_stock_move_in_id(self):
        model_product_compromise = self.env['product.compromise']
        product_in_compromises = model_product_compromise.search(
            [('stock_move_in_id.id', '=', self.stock_move_in_id.id)])
        compromise_in = sum(
            [product_in_compromise.qty_compromise for product_in_compromise in
             product_in_compromises])
        self.compromise_max = self.stock_move_in_id.product_uom_qty - compromise_in # noqa
        return {}

    # @api.multi
    def confirm(self):
        model_product_compromise = self.env['product.compromise']
        product_compromises = model_product_compromise.search(
            [('stock_move_out_id.id', '=', self.stock_move_out_id.id),
             ('state', '=', 'assigned')])
        compromise = sum(
            [product_compromise.qty_compromise for product_compromise in
             product_compromises])
        product_in_compromises = model_product_compromise.search(
            [('stock_move_in_id.id', '=', self.stock_move_in_id.id)])
        compromise_in = sum(
            [product_in_compromise.qty_compromise for product_in_compromise in
             product_in_compromises])
        if (self._context.get('qty') - self.stock_move_out_id.reserved_availability - compromise) < self.qty_compromise: # noqa
            raise ValidationError(
                _("the quantity of products must be less than the quantity \
                  of products in the movement"))
        elif self.qty_compromise > (self.stock_move_in_id.product_uom_qty - compromise_in): # noqa
            raise ValidationError(
                _("the quantity of products must be less than the quantity \
                  of incoming products"))
        model_product_compromise.create(
            {'qty_compromise': self.qty_compromise,
             'stock_move_in_id': self.stock_move_in_id.id,
             'stock_move_out_id': self.stock_move_out_id.id})


class Liberate(models.TransientModel):
    _name = "liberate"

    stock_move_in_id = fields.Many2one(
        'stock.move',
        'Incoming',
        domain=lambda self: [('id', 'in', self._context.get('lista')),
                             ('state', '!=', 'done')])

    # @api.multi
    def confirm(self):
        product_compromise_obj = self.env['product.compromise']
        product_compromise = product_compromise_obj.search(
            [('stock_move_in_id', '=', self.stock_move_in_id.id),
             ('stock_move_out_id', '=', self._context.get('move_out'))])
        product_compromise.unlink()


class Reserve(models.TransientModel):
    _name = "reserve"

    qty_reserve = fields.Float('Quantity', required=True)
    stock_move_out_id = fields.Many2one(
        'stock.move',
        'Outgoing products',
        default=lambda self: self._context.get('move_out'),
        required=True)

    # @api.multi
    def confirm(self):
        move = self.stock_move_out_id
        move.action_assign_qty(self.qty_reserve, move.dis_product,
                               self._context.get('compromise'))
