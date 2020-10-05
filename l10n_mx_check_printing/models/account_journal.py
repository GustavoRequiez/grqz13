from odoo import models, fields


class AccountJournal(models.Model):
    _inherit = "account.journal"

    mx_check_layout = fields.Selection(
        string="Check Layout",
        help="Select the format corresponding to the bank you will be "
        "printing your checks on. In order to disable the printing feature, "
        "select 'None'.",
        selection=[
            ('disabled', 'None'),
            ('l10n_mx_check_printing.action_print_check_generic',
             'Generic Check'),
            ('l10n_mx_check_printing.action_print_check_banamex',
             'Banamex Check'),
            ('l10n_mx_check_printing.action_print_check_bbva_bancomer',
             'BBVA Bancomer Check'),
            ('l10n_mx_check_printing.action_print_check_santander',
             'Santander Check'),
            ('l10n_mx_check_printing.action_print_check_scotiabank',
             'Scotiabank Check'),
            ('l10n_mx_check_printing.action_print_check_hsbc', 'HSBC Check'),
        ],
        default="l10n_mx_check_printing.action_print_check_generic")
