# Copyright 2017 Humanytek.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
from odoo import models
_logger = logging.getLogger(__name__)


class StockMove(models.Model):
    _name = "stock.move"
    _inherit = ['stock.move', 'sale.order.observation']

    def _compute_observation(self):
        for move in self:
            move.sale_line_observation = move.sale_line_id.observation
