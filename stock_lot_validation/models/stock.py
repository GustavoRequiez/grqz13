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

from odoo import api, models, _
import logging
_logger = logging.getLogger(__name__)


class StockMove(models.Model):
    _inherit = 'stock.move'

    def action_show_details(self):
        stock_lot_ids = self.env['stock.quant'].search(
            [('product_id', '=', self.product_id.id),
             ('location_id', '=', self.location_id.id)]).ids
        self.env.context = {'stock_lot_ids': stock_lot_ids}
        return super(StockMove, self).action_show_details()


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    @api.onchange('lot_id', 'qty_done')
    def onchange_lot(self):
        res = {}
        location = self.location_id
        if location.usage == 'supplier' or location.usage == 'inventory':
            return res
        if self.lot_id and self.qty_done > 0:
            StockQuant = self.env['stock.quant']
            quants = StockQuant.search([
                ('product_id.id', '=', self.product_id.id),
                ('lot_id.id', '=', self.lot_id.id),
                ('location_id.id', '=', self.location_id.id),
            ])
            qty_total = sum([quant.quantity for quant in quants])
            if self.qty_done > qty_total:
                self.qty_done = 0
                message = "No tiene stock de este lote"
                res['warning'] = {'title': _('Warning'), 'message': message}
        return res
