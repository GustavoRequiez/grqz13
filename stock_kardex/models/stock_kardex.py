# -*- coding: utf-8 -*-
###############################################################################
#
#    Odoo, Open Source Management Solution
#    Copyright (C) 2017 Humanytek (<www.humanytek.com>).
#    Rubén Bravo <rubenred18@gmail.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################

from odoo import api, fields, models
import logging
_logger = logging.getLogger(__name__)


class StockKardex(models.TransientModel):
    _name = "stock.kardex"

    # @api.multi
    def calculate(self):
        StockMove = self.env['stock.move']
        StockKardexDetail = self.env['stock.kardex.detail']
        qty = 0
        qty_reserve = 0

        stock_moves = StockMove.search([
            ('product_id.id', '=', self.product_id.id),
            ('date', '>=', self.date_start),
            ('date', '<=', self.date_end),
            ('state', '=', 'done'),
            '|',
            ('location_id', '=', self.location_id.id),
            ('location_dest_id', '=', self.location_id.id)],
            order='date')

        stock_moves_ini = StockMove.search([
            ('product_id.id', '=', self.product_id.id),
            ('date', '<', self.date_start),
            ('state', '=', 'done'),
            '|',
            ('location_id', '=', self.location_id.id),
            ('location_dest_id', '=', self.location_id.id)],
            order='date'
        )
        for move in stock_moves_ini:
            if self.location_id.id == move.location_id.id:
                if move.location_dest_id.id != 616:
                    qty -= move.product_uom_qty
                else:
                    qty += move.product_uom_qty

        stock_moves_reserved = StockMove.search([
            ('product_id.id', '=', self.product_id.id),
            ('date', '>=', self.date_start),
            ('date', '<=', self.date_end),
            ('state', 'in', ['assigned', 'confirmed']),
            ('location_id', '=', self.location_id.id)],
            order='date')

        for moves_reserved in stock_moves_reserved:
            qty_reserve += moves_reserved.reserved_availability

        #self.write({'stock_start': qty})
        qty_ini = qty
        StockKardexDetail.search([]).unlink()
        for stock_move in stock_moves:
            product_incomming = 0
            product_outgoing = 0
            if stock_move.location_id.id != stock_move.location_dest_id.id:
                if self.location_id.id == stock_move.location_id.id:
                    product_outgoing = stock_move.product_uom_qty
                    qty -= stock_move.product_uom_qty
                else:
                    product_incomming = stock_move.product_uom_qty
                    qty += stock_move.product_uom_qty

                StockKardexDetail.create({
                    'stock_move_id': stock_move.id,
                    'product_id': self.product_id.id,
                    'stock_kardex_id': self.id,
                    'qty_product': qty,
                    'product_incomming': product_incomming,
                    'product_outgoing': product_outgoing})
        self.write({'stock_end': qty, 'qty_reserve': qty_reserve,
                    'stock_start': qty_ini})

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'stock.kardex',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': self.id,
            'views': [(False, 'form')],
            'target': 'new',
        }

    @api.model
    def _get_default_location_id(self):
        location = self.env.ref('stock.stock_location_stock',
                                raise_if_not_found=False)
        return location and location.id or False

    product_id = fields.Many2one('product.product', 'Product', required=True)
    location_id = fields.Many2one('stock.location', 'Location', required=True,
                                  default=_get_default_location_id)
    date_start = fields.Datetime('Start Date',
                                 required=True)
    date_end = fields.Datetime('End Date',
                               required=True)
    stock_start = fields.Float('Starting stock', readonly=True)
    stock_end = fields.Float('Ending stock', readonly=True,)
    qty_reserve = fields.Float('Total Reserved Product', readonly=True,)

    stock_kardex_detail_ids = fields.One2many('stock.kardex.detail',
                                              'stock_kardex_id',
                                              'Detail')


class StockKardexDetail(models.TransientModel):
    _name = "stock.kardex.detail"

    stock_kardex_id = fields.Many2one('stock.kardex', 'Kardex')
    stock_move_id = fields.Many2one('stock.move', 'Move', readonly=True)
    qty_product = fields.Float('Quantity Total', readonly=True)
    product_incomming = fields.Float('Incoming Products', readonly=True)
    product_outgoing = fields.Float('Outgoing Products', readonly=True)
    move_qty_product = fields.Float(related='stock_move_id.product_uom_qty',
                                    string='Quantity', readonly=True, store=False)
    move_date = fields.Datetime(related='stock_move_id.date',
                                string='Date', readonly=True, store=False)
    location_id = fields.Many2one(related='stock_move_id.location_id',
                                  string='Source Location',
                                  readonly=True, store=False)
    location_dest_id = fields.Many2one(
        related='stock_move_id.location_dest_id',
        string='Destination Location',
        readonly=True, store=False)
