# Copyright 2018 Vauxoo (https://www.vauxoo.com) <info@vauxoo.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    association_ids = fields.One2many('account.association', 'move_id',
                                      string="Associations")

    # @api.multi
    def assign_outstanding_credit(self, credit_aml_id):
        res = super(AccountMove, self).assign_outstanding_credit(
            credit_aml_id)
        association_ids = self.association_ids.filtered(
            lambda a: a.move_line_id.id == credit_aml_id)
        vals = {
            'move_id': self.id,
            'move_line_id': credit_aml_id,
            'date': fields.Date.today()}
        if association_ids:
            association_ids.update(date=fields.Date.today())
        else:
            self.env['account.association'].create(vals)
        return res
