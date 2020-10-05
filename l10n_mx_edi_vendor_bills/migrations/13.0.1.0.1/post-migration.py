from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    reset_sat_status_vendor_bills(cr)


def reset_sat_status_vendor_bills(cr):
    env = api.Environment(cr, SUPERUSER_ID, {})
    vendor_bills = env['account.move'].search([
        ('type', 'in', ('in_invoice', 'in_refund')),
        ('state', '=', 'draft'),
        ('l10n_mx_edi_sat_status', '!=', 'undefined'),
    ])
    vendor_bills.write({'l10n_mx_edi_sat_status': 'undefined'})
