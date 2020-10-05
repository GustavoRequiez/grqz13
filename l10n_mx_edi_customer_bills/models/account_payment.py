from odoo import models


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    def l10n_mx_edi_is_required(self):
        get_param = self.env['ir.config_parameter'].sudo().get_param
        if get_param('l10n_mx_edi.avoid_stamp_payments'):
            return False
        return super(AccountPayment, self).l10n_mx_edi_is_required()
