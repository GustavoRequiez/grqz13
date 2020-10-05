import time
from odoo.tests import tagged
from odoo.tests.common import Form
from odoo.addons.account.tests.account_test_classes import AccountingTestCase


@tagged('post_install', '-at_install')
class TestMXCheckPrinting(AccountingTestCase):

    def setUp(self):
        super(TestMXCheckPrinting, self).setUp()
        self.invoice_model = self.env['account.move']
        self.register_payments_model = self.env['account.payment.register']

        self.partner_jackson = self.env.ref("base.res_partner_10")
        self.product = self.env.ref("product.product_product_4")
        self.payment_method_check = self.env.ref(
            "account_check_printing.account_payment_method_check")
        self.bank_journal = self.env['account.journal'].search([
            ('type', '=', 'bank')], limit=1).copy({
                'name': 'Bank', 'code': 'BNK67'})
        self.bank_journal.check_manual_sequencing = True
        self.bank_journal.mx_check_layout = "l10n_mx_check_printing.action_print_check_bbva_bancomer" # noqa
        self.account_payable = self.env['account.account'].search(
            [('user_type_id', '=', self.env.ref(
                'account.data_account_type_payable').id)], limit=1)
        self.account_expenses = self.env['account.account'].search(
            [('user_type_id', '=', self.env.ref(
                'account.data_account_type_expenses').id)], limit=1)

    def create_invoice(self, amount=100):
        invoice = self.invoice_model.create({
            'partner_id': self.partner_jackson.id,
            'name': "Supplier Invoice",
            'type': "in_invoice",
            'invoice_date': time.strftime('%Y') + '-06-26',
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product.id,
                'quantity': 1,
                'price_unit': amount,
                'name': 'something',
                'account_id': self.account_expenses.id,
            })]
        })
        invoice.action_post()
        return invoice

    def create_payment(self, invoices):
        ctx = {'active_model': 'account.move', 'active_ids': invoices.ids}
        payment_register = Form(self.env['account.payment'].with_context(ctx))
        payment_register.payment_date = time.strftime('%Y') + '-07-15'
        payment_register.journal_id = self.bank_journal
        payment_register.communication = 'With Check'
        payment_register.amount = invoices.amount_total
        payment_register.payment_method_id = self.payment_method_check
        payment = payment_register.save()
        return payment

    def test_print_check(self):
        invoice = self.create_invoice()
        payment = self.create_payment(invoice)

        payment.print_checks()
        self.assertEqual(payment.state, 'sent')
