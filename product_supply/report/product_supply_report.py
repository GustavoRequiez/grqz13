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

from datetime import datetime
from collections import OrderedDict
from odoo import api, models
import logging
_logger = logging.getLogger(__name__)


class ProductSupply(models.AbstractModel):
    _name = 'report.product_supply.report_product_supply'

    @api.model
    def _get_report_values(self, docids, data=None):
        docids = data['extra_data']['ids']
        model_stock_move = self.env['stock.move']
        docs = model_stock_move.browse(docids)
        data['extra_data']['moves'] = {b: OrderedDict(
            sorted(v.items(), key=lambda x: x[0])) for b, v in data[
                'extra_data']['moves'].items()}
        return {
            'doc_ids': docids,
            'docs': docs,
            'data': data['extra_data'],
            'env': self.env
        }
