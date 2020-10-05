# Copyright 2018 Vauxoo (https://www.vauxoo.com) <info@vauxoo.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import api, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    # @api.multi
    def remove_move_reconcile(self):
        self.env['account.association'].search([
            ('move_line_id', 'in', self.ids)]).unlink()
        return super(AccountMoveLine, self).remove_move_reconcile()
