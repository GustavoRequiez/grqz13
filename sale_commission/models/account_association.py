# Copyright 2018 Vauxoo (https://www.vauxoo.com) <info@vauxoo.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models


class AccountAssociation(models.Model):
    _name = 'account.association'

    # @api.multi
    def _get_total_amount(self):
        self.ensure_one()
        amount = 0.0
        if self.move_id.type in ('out_invoice', 'in_refund'):
            amount = sum([
                p.amount for p in self.move_line_id.matched_debit_ids
                if p.debit_move_id in self.move_id.move_id.line_ids])
            return amount
        amount = sum([
            p.amount for p in self.move_line_id.matched_credit_ids
            if p.credit_move_id in self.move_id.move_id.line_ids])
        return amount

    @api.depends('move_id')
    def _compute_payment_amount(self):
        for record in self:
            record.payment_amount = record._get_total_amount()

    move_id = fields.Many2one('account.move', ondelete='cascade',
                              help="Invoice")
    move_line_id = fields.Many2one(
        'account.move.line', ondelete='cascade',
        help="Move where the payment was registered")
    date = fields.Date(
        help="Date where the payment was registered in the system by the user")
    payment_amount = fields.Float(
        compute='_compute_payment_amount',
        help="amount of the payment for this invoice")

    # Performance fields
    # This fields help us to avoid monster queries when the report is generated
    aml_state = fields.Selection(
        related='move_line_id.move_id.state', readonly=True, store=True)
    aml_invoice_type = fields.Selection(
        related='move_line_id.move_id.type', readonly=True, store=True)
