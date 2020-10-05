# Copyright 2017 Humanytek.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
from odoo import fields, models
_logger = logging.getLogger(__name__)


class MrpProduction(models.Model):
    _name = "mrp.production"
    _inherit = ['mrp.production', 'sale.order.observation']

    sale_type_id = fields.Char(
        related='sale_id.type_id.name',
        string='Sale Order Type',
        readonly=True,
        store=False)
    type_priority = fields.Integer(
        related='sale_id.type_id.priority',
        string='Priority',
        readonly=True,
        store=False)

    def _compute_observation(self):
        for mrp in self:
            line = mrp.move_finished_ids.mapped('move_dest_ids.sale_line_id')
            mrp.sale_line_observation = line.observation if line else ''
