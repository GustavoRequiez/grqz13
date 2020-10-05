# Copyright 2017 Humanytek.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
from odoo import models
_logger = logging.getLogger(__name__)


class AccountInvoiceLine(models.Model):
    _name = "account.move.line"
    _inherit = ['account.move.line', 'sale.order.observation']
