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

    compromise_qty_move = fields.Float('Compromise',
                                       compute='_compute_compromise_qty_move', readonly=True)

    # @api.one
    def _compute_compromise_qty_move(self):
        ProductCompromise = self.env['product.compromise']
        product_compromises = ProductCompromise.search([
            ('stock_move_in_id.id', '=', self.id),
            ('state', '=', 'assigned')])
        self.compromise_qty_move = sum([product_compromise.qty_compromise
                                        for product_compromise in
                                        product_compromises])
