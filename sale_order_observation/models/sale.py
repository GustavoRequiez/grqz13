# Copyright 2017 Humanytek.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
from odoo import api, fields, models
_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _name = "sale.order"
    _inherit = 'sale.order'

    type_id = fields.Many2one('sale.order.type', 'Type')


class SaleOrderLine(models.Model):
    _name = "sale.order.line"
    _inherit = ['sale.order.line', 'sale.order.observation']

    # @api.multi
    def _prepare_invoice_line(self, qty):
        res = super(SaleOrderLine, self)._prepare_invoice_line(qty)
        res['observation'] = self.observation
        return res


class SaleOrderType(models.Model):
    _name = "sale.order.type"

    name = fields.Char('Type', required=True)
    active = fields.Boolean(default=True)
    priority = fields.Integer(required=True, default=1)
