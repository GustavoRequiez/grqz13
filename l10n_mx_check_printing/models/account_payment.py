from odoo import _, models
from odoo.tools.misc import formatLang, format_date
from odoo.exceptions import UserError


class AccountPayment(models.Model):
    _inherit = "account.payment"

    def do_print_checks(self):
        mx_check_layout = self[0].journal_id.mx_check_layout
        if mx_check_layout != 'disabled':
            self.write({'state': 'sent'})
            return self.env.ref(mx_check_layout).report_action(self)
        if self.company_id.country_id == self.env.ref('base.mx'):
            raise UserError(
                _("There is no check layout configured.\n"
                  "Make sure the proper check printing module is installed "
                  "and its configuration (in Journals > 'Advance Settings' "
                  "tab) is correct."))
        return super(AccountPayment, self).do_print_checks()

    def get_pages(self):
        """ Returns the data structure used by the template : a list of dicts
        containing what to print on pages.
        """
        pages = []
        pages.append({
            'sequence_number': self.check_number,
            'payment_date': format_date(self.env, self.payment_date,
                                        date_format='dd-MMM-YYYY'),
            'partner_id': self.partner_id,
            'partner_name': (self.partner_id.name or '').upper(),
            'currency': self.currency_id,
            'state': self.state,
            'amount': formatLang(
                self.env, self.amount,
                currency_obj=self.currency_id),
            'amount_in_word': '(* ' + self.check_amount_in_words.upper() + ' *)', # noqa
        })
        return pages
