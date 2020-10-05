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


class StockMove(models.Model):
    _name = "stock.move"
    _inherit = 'stock.move'

    product_brand = fields.Char(related='product_id.product_brand_id.name',
                                string='Brand', readonly=True, store=True)
    product_default_code = fields.Char(related='product_id.default_code',
                                       string='Default code',
                                       readonly=True, store=True)

    mrp_date = fields.Datetime(
        compute='_compute_mrp_date',
        string='Date_planned',
        search='_search_date_planned',
        readonly=True,
        store=False)
    lotes = fields.Char(compute='_compute_lote',
                        string='Lotes',
                        readonly=True,
                        store=False)
    sale_order_type_id = fields.Char(compute='_compute_type',
                                     string='Sale Order Type',
                                     readonly=True,
                                     store=False)

    # @api.one
    def _compute_mrp_date(self):
        for move in self.mapped('raw_material_production_id'):
            move.move_raw_ids.update({'mrp_date': move.date_planned_start})

    # @api.multi
    def _search_date_planned(self, operator, value):
        model_mrp_production = self.env['mrp.production']
        moves = model_mrp_production.search(
            [('date_planned_start', operator, value)])
        list_ids = moves.mapped('move_raw_ids.id')
        return [('id', 'in', list_ids)]

    # @api.one
    def _compute_lote(self):
        for moves in self.filtered('move_line_ids.lot_id'):
            lots = ""
            for move in moves.mapped('move_line_ids').filtered('product_qty'):
                lots += '%s  %s,' % (move.lot_id.name or '', move.product_qty)
            moves.lotes = lots

    # @api.one
    def _compute_type(self):
        MrpProduction = self.env['mrp.production']
        productions = MrpProduction.search([
            ('move_raw_ids.id', 'in', [self.id])])
        if productions:
            if productions[0].sale_id:
                self.sale_order_type_id = productions[0].sale_id.type_id.name
