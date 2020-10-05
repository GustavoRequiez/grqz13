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

from odoo import api, models
import logging
import datetime
from collections import defaultdict
_logger = logging.getLogger(__name__)


class ProductSupply(models.TransientModel):
    _name = "product.supply"

    # @api.multi
    def confirm(self):
        dict_moves = defaultdict(lambda: defaultdict(dict))
        moves = self.env['stock.move'].browse(self._context.get('active_ids'))
        for move in moves:
            brand = move.product_id.product_brand_id.name or 'NA'
            # pylint: disable=W0640
            for line in move.mapped('move_line_ids').filtered(
                lambda m: m.product_id.id == move.product_id.id and
                    m.product_qty > 0):
                dict_moves[brand][line.product_id.default_code].update({
                    str(line.lot_id.id if line.lot_id else 0): {
                        'qty': sum([l.product_qty for m in moves.mapped(
                            'move_line_ids') for l in m.filtered(
                                lambda a: a.product_id.id == line.product_id.id
                                and a.lot_id.id == line.lot_id.id)])
                        if line.lot_id else sum([
                            m.product_qty for m in moves.mapped(
                                'move_line_ids') for l in m.filtered(
                                    lambda a: a.product_id.id ==
                                    line.product_id.id and not line.lot_id)]),
                        'move': line.id}})
        extra_data = dict()
        extra_data['ids'] = [value.id for value in moves]
        extra_data['moves'] = dict_moves
        extra_data['date'] = datetime.datetime.now().strftime(
            '%d-%m-%Y %H:%M:%S')
        extra_data['origin'] = moves[0].location_id.name
        extra_data['dest'] = moves[0].location_dest_id.name
        data = dict()
        data['extra_data'] = extra_data
        product_supply_report = self.env.ref(
            'product_supply.action_print_report_product_supply')
        return product_supply_report.report_action(self, data=data)
