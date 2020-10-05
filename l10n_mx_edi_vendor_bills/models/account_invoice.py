# Copyright 2017, Jarsa Sistemas, S.A. de C.V.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).
# pylint: disable=W1505
import base64
from codecs import BOM_UTF8

from odoo import _, api, models

BOM_UTF8U = BOM_UTF8.decode('UTF-8')
CFDI_SAT_QR_STATE = {
    'No Encontrado': 'not_found',
    'Cancelado': 'cancelled',
    'Vigente': 'valid',
}


class AccountMove(models.Model):
    _inherit = 'account.move'

    def generate_xml_attachment(self):
        self.ensure_one()
        if not self.l10n_mx_edi_cfdi:
            return False
        fname = ("%s-%s-MX-Bill-%s.xml" % (
            self.journal_id.code, self.invoice_payment_ref,
            self.company_id.partner_id.vat or '')).replace('/', '')
        data_attach = {
            'name': fname,
            'datas': base64.encodestring(
                self.l10n_mx_edi_cfdi and
                self.l10n_mx_edi_cfdi.lstrip() or ''),
            'description': _('XML signed from Invoice %s.') % self.name,
            'res_model': self._name,
            'res_id': self.id,
        }
        self.l10n_mx_edi_cfdi_name = fname
        return self.env['ir.attachment'].with_context({}).create(data_attach)

    def create_adjustment_line(self, xml_amount):
        """If the invoice has difference with the total in the CFDI is
        generated a new line with that adjustment if is found the account to
        assign in this lines. The account is assigned in a system parameter
        called 'adjustment_line_account_MX'"""
        account_id = self.env['ir.config_parameter'].sudo().get_param(
            'adjustment_line_account_MX', '')
        if not account_id:
            return False
        self.invoice_line_ids.create({
            'account_id': account_id,
            'name': _('Adjustment line'),
            'quantity': 1,
            'price_unit': xml_amount - self.amount_total,
            'invoice_id': self.id,
        })
        return True

    def post(self):
        """Sync SAT status if not set yet"""
        res = super(AccountMove, self).post()
        vendor_bills = self.filtered(
            lambda inv:
            inv.is_purchase_document()
            and inv.l10n_mx_edi_cfdi_name)
        vendor_bills.l10n_mx_edi_update_sat_status()
        return res

    def button_draft(self):
        """Reset SAT status when a vendor bill is reset to draft"""
        res = super().button_draft()
        # not using is_required since it doesn't take into account vendor bills
        vendor_bills = self.filtered(
            lambda x:
            x.is_purchase_document()
            and x.l10n_mx_edi_sat_status != 'undefined')
        vendor_bills.write({'l10n_mx_edi_sat_status': 'undefined'})
        return res


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    @api.model
    def _default_account(self):
        """This method was forwardported from v12, please take
        extra care reviewing it.
        """
        if self._context.get('journal_id'):
            journal = self.env['account.journal'].browse(
                self._context.get('journal_id'))
            if self._context.get('type') in ('out_invoice', 'in_refund'):
                return journal.default_credit_account_id.id
            return journal.default_debit_account_id.id
