# Copyright 2018 Vauxoo (https://www.vauxoo.com) <info@vauxoo.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).
from odoo import api, fields, models


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    def _make_association(self):
        self.ensure_one()
        lines = []
        for invoice in self.move_ids:
            lines += [(invoice.id, vals.get('payment_id'))
                      for vals in invoice._get_payments_vals()
                      if vals.get('account_payment_id') == self.id]
        for line in lines:
            self.env['account.association'].create({
                'move_id': line[0],
                'move_line_id': line[1],
                'date': fields.Date.today(),
            })

    # @api.multi
    def post(self):
        res = super(AccountPayment, self).post()
        for record in self:
            record._make_association()
        return res
