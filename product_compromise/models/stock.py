# Copyright 2017 Humanytek.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
from odoo import api, fields, models
_logger = logging.getLogger(__name__)


class StockMove(models.Model):
    _inherit = 'stock.move'

    product_compromise_ids = fields.One2many(
        'product.compromise',
        'stock_move_out_id',
        'Compromise Products')

    compromise_qty = fields.Float(
        'Compromise',
        compute='_compute_compromise',
        readonly=True)

    product_qty_product = fields.Float(
        compute='_compute_qty_product', readonly=True, store=False)

    product_incoming_qty = fields.Float(
        related='product_id.incoming_qty',
        string='Total Incoming Product',
        readonly=True,
        store=False)

    total_compromise_product = fields.Float(
        compute='_compute_compromise',
        readonly=True,
        store=False)

    total_reserved_product = fields.Float(
        compute='_compute_total_reserved_product',
        readonly=True,
        store=False)

    dis_product_in = fields.Float(
        'Availability Incoming Product',
        compute='_compute_dis_product',
        readonly=True,
        store=False)

    dis_product = fields.Float(
        'Availability Product',
        compute='_compute_dis_product',
        readonly=True,
        store=False)

    def _compute_compromise(self):
        for move in self:
            compromise = move.env['product.compromise'].search(
                [('product_id.id', '=', move.product_id.id),
                 ('state', '=', 'assigned')])
            move.compromise_qty = sum(
                [product_compromise.qty_compromise for product_compromise in
                 move.product_compromise_ids if
                 product_compromise.state == 'assigned'])
            move.total_compromise_product = sum(
                [product_compromise.qty_compromise for product_compromise in
                 compromise])

    def _compute_total_reserved_product(self):
        for move in self:
            moves = self.search(
                [('product_id.id', '=', move.product_id.id),
                 ('state', 'in',
                  ('assigned', 'confirmed', 'partially_available')),
                 ('location_id.usage', '=', 'internal')])
            move.total_reserved_product = sum(
                [stock_move.reserved_availability for stock_move in moves if
                 stock_move.product_id.id == move.product_id.id])

    def _compute_dis_product(self):
        for move in self:
            move.dis_product_in = move.product_incoming_qty - move.total_compromise_product # noqa
            move.dis_product = move.product_qty_product - move.total_reserved_product # noqa

    # @api.multi
    def _compute_qty_product(self):
        stock_location_obj = self.env['stock.location']
        stock_location = stock_location_obj.search(
            [('default_location', '=', True),
             ('company_id', '=', self.env.user.company_id.id)], limit=1)
        quant_obj = self.env['stock.quant']

        for move in self:
            quant_data = quant_obj.read_group([
                ('product_id', '=', move.product_id.id),
                ('location_id', 'child_of', stock_location.id)],
                ['product_id', 'quantity'], ['product_id'])
            if quant_data:
                move.product_qty_product = quant_data[0].get('quantity', 0.0)

    # @api.multi
    def action_compromise(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'compromise',
            'view_mode': 'form',
            'view_type': 'form',
            'context': {'product_id': self.product_id.id,
                        'move_out': self.id,
                        'qty': self.product_uom_qty,
                        'location_id': self.location_id.id},
            'views': [(False, 'form')],
            'target': 'new',
            }

    # @api.multi
    def action_liberate(self):
        lista = []
        for product_compromise in self.product_compromise_ids:
            lista.append(product_compromise.stock_move_in_id.id)
            _logger.info(lista)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'liberate',
            'view_mode': 'form',
            'view_type': 'form',
            'context': {'product_id': self.product_id.id,
                        'move_out': self.id,
                        'lista': lista},
            'views': [(False, 'form')],
            'target': 'new',
            }

    def _action_cancel(self):
        if super(StockMove, self)._action_cancel():
            product_compromise = self.env['product.compromise']
            product_compromises = product_compromise.search([(
                'stock_move_out_id.state', '=', 'cancel')])
            product_compromises.unlink()
        return True

    def _action_done(self):
        if super(StockMove, self)._action_done():
            for moves in self:
                product_compromises = self.env['product.compromise'].search(
                    [('stock_move_in_id.id', '=', moves.id)])
                for product_compromise in product_compromises:
                    move = product_compromise.stock_move_out_id
                    compromise_qty = sum(
                        [compromise.qty_compromise for
                         compromise in move.product_compromise_ids if
                         compromise.state == 'done' and
                         compromise.stock_move_in_id ==
                         product_compromise.stock_move_in_id]) or 0.0
                    if move.reserved_availability < move.product_uom_qty:
                        move._update_reserved_quantity(
                            compromise_qty, compromise_qty,
                            move.location_id, strict=False)
        return True

    # @api.multi
    def action_reserve(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'reserve',
            'view_mode': 'form',
            'view_type': 'form',
            'context': {'compromise': self.compromise_qty,
                        'move_out': self.id,
                        'qty': self.product_uom_qty},
            'views': [(False, 'form')],
            'target': 'new',
            }

    # @api.multi
    def action_assign_qty(self, need, available_quantity, qty_compromise):
        moves_to_assign = self.env['stock.move']
        moves = self.filtered(
            lambda m: m.state in ['confirmed', 'waiting', 'assigned',
                                  'partially_available'])
        sml_rec = self.env['stock.move.line']
        for move in moves:
            qty = move.product_qty - move.reserved_availability - \
                qty_compromise
            qty = min(qty, need - move.reserved_availability)
            if qty == 0:
                continue
            taken_quantity = move._update_reserved_quantity(
                qty, available_quantity, move.location_id, strict=False)
            if need == taken_quantity:
                moves_to_assign |= move
            moves_to_assign.write({'state': 'assigned'})
            try:
                sml_rec.search(
                    [('move_id', '=', move.id),
                     ('product_uom_qty', '=', 0)]).unlink()
            except BaseException as error:
                _logger.error(
                    'Error trying to delete '
                    'stock move line: %s', error)
