# See LICENSE file for full copyright and licensing details.

import base64
import os

from lxml import etree
from lxml.objectify import fromstring

from odoo.tests.common import TransactionCase
from odoo.tools import misc


class MxEdiCustomerBills(TransactionCase):

    def setUp(self):
        super(MxEdiCustomerBills, self).setUp()
        self.invoice_obj = self.env['account.move']
        self.attach_wizard_obj = self.env['attach.xmls.wizard']
        self.partner = self.env.ref('base.res_partner_1')
        self.env.ref('base.res_partner_3').vat = 'XEXX010101000'
        self.product = self.env.ref('product.product_product_24')
        self.key = 'bill.xml'
        self.key_credit_note = 'credit_note.xml'
        self.key_credit_invoice = 'credit_invoice.xml'
        self.xml_str = misc.file_open(os.path.join(
            'l10n_mx_edi_customer_bills', 'tests', self.key)
        ).read().encode('UTF-8')
        self.xml_str_credit_invoice = misc.file_open(os.path.join(
            'l10n_mx_edi_customer_bills', 'tests', self.key_credit_invoice)
        ).read().encode('UTF-8')
        self.xml_str_credit_note = misc.file_open(os.path.join(
            'l10n_mx_edi_customer_bills', 'tests', self.key_credit_note)
        ).read().encode('UTF-8')
        self.xml_tree = fromstring(self.xml_str)
        self.tax = self.env.ref('l10n_mx.1_tax1')
        self.tax.type_tax_use = 'sale'
        tag_id = self.env['account.account.tag'].search([
            ('name', 'ilike', 'iva')], limit=1)
        self.tax.invoice_repartition_line_ids.tag_ids |= tag_id

    def test_001_create_vendor_bill(self):
        """Create a vendor bill from xml and check its values"""
        # create invoice
        res = self.attach_wizard_obj.with_context(
            l10n_mx_edi_invoice_type='out').check_xml({
                self.key: base64.b64encode(self.xml_str).decode('UTF-8')})
        invoices = res.get('invoices', {})
        inv_id = invoices.get(self.key, {}).get('invoice_id', False)
        self.assertTrue(inv_id, "Error: Invoice creation")
        # check values
        inv = self.invoice_obj.browse(inv_id)
        xml_amount = float(self.xml_tree.get('Total', 0.0))
        self.assertEqual(inv.amount_total, xml_amount, "Error: Total amount")
        xml_vat_receiver = self.xml_tree.Receptor.get('Rfc', '').upper()
        self.assertEqual(
            inv.partner_id.vat, xml_vat_receiver, "Error: Receptor")
        xml_vat_emitter = self.xml_tree.Emisor.get('Rfc', '').upper()
        self.assertEqual(self.env.company.vat, xml_vat_emitter,
                         "Error: Emisor")
        xml_tfd = self.invoice_obj.l10n_mx_edi_get_tfd_etree(self.xml_tree)
        uuid = False if xml_tfd is None else xml_tfd.get('UUID', '')
        xml_folio = '%s%s|%s' % (self.xml_tree.get('Serie', ''), self.xml_tree.get('Folio', ''), uuid.split('-')[0])

        self.assertEqual(inv.invoice_payment_ref, xml_folio, "Error: Reference - folio")

    def test_002_create_vendor_bill_from_partner(self):
        """Create a vendor bill without a existing partner"""
        self.xml_tree.Receptor.set('Rfc', 'COPU930915KW7')
        self.xml_tree.Receptor.set('Nombre', 'USUARIO COMP PRUEBA')
        xml64 = base64.b64encode(etree.tostring(
            self.xml_tree, pretty_print=True, xml_declaration=True,
            encoding='UTF-8')).decode('UTF-8')
        self.attach_wizard_obj.with_context(
            l10n_mx_edi_invoice_type='out').create_partner(xml64, self.key)
        res = self.attach_wizard_obj.with_context(
            l10n_mx_edi_invoice_type='out').check_xml({self.key: xml64})
        invoices = res.get('invoices', {})
        inv_id = invoices.get(self.key, {}).get('invoice_id', False)
        self.assertTrue(inv_id, "Error: Invoice creation")
        # check partner
        inv = self.invoice_obj.browse(inv_id)
        partner = inv.partner_id
        self.assertEqual(partner.vat, self.xml_tree.Receptor.get('Rfc'),
                         "Error: Partner RFC")
        self.assertEqual(partner.name, self.xml_tree.Receptor.get('Nombre'),
                         "Error: Partner Name")
        # Check invoice values
        xml_amount = float(self.xml_tree.get('Total', 0.0))
        self.assertEqual(inv.amount_total, xml_amount, "Error: Total amount")
        xml_tfd = self.invoice_obj.l10n_mx_edi_get_tfd_etree(self.xml_tree)
        uuid = False if xml_tfd is None else xml_tfd.get('UUID', '')
        xml_folio = '%s%s|%s' % (self.xml_tree.get('Serie', ''), self.xml_tree.get('Folio', ''), uuid.split('-')[0])
        self.assertEqual(inv.invoice_payment_ref, xml_folio, "Error: Reference")

    def test_003_attach_xml_to_invoice_without_uuid(self):
        """Test attach xml in a invoice without uuid and with the same
        reference
        """
        res = self.attach_wizard_obj.with_context(
            l10n_mx_edi_invoice_type='out').check_xml({
                self.key: base64.b64encode(self.xml_str).decode('UTF-8')})
        invoices = res.get('invoices', {})
        inv_id = invoices.get(self.key, {}).get('invoice_id', False)
        inv = self.invoice_obj.browse(inv_id)
        inv.l10n_mx_edi_cfdi_name = False
        res = self.attach_wizard_obj.with_context(
            l10n_mx_edi_invoice_type='out').check_xml({
                self.key: base64.b64encode(self.xml_str).decode('UTF-8')})
        invoices = res.get('invoices', {})
        inv_id = invoices.get(self.key, {}).get('invoice_id', False)
        self.assertEqual(inv_id, inv.id,
                         "Error: attachment generation")
        self.assertTrue(inv.l10n_mx_edi_retrieve_attachments(),
                        "Error: no attachment")

    def test_004_create_invoice_two_times(self):
        """Try to create a invoice two times"""
        res = self.attach_wizard_obj.with_context(
            l10n_mx_edi_invoice_type='out').check_xml({
                self.key: base64.b64encode(self.xml_str).decode('UTF-8')})
        invoices = res.get('invoices', {})
        inv = invoices.get(self.key, {}).get('invoice_id', False)
        self.assertTrue(inv, "Error: Invoice creation")
        res = self.attach_wizard_obj.with_context(
            l10n_mx_edi_invoice_type='out').check_xml({
                self.key: base64.b64encode(self.xml_str).decode('UTF-8')})
        invoices = res.get('invoices', {})
        inv2 = invoices.get(self.key, {}).get('invoice_id', False)
        self.assertTrue(inv == inv2, "Error: invoice created in two times")

    def test_005_create_invoice_and_check_credit_note(self):
        """Checks the credit note of an imported invoice.
        """
        res = self.attach_wizard_obj.check_xml({
            self.key_credit_invoice: base64.b64encode(self.xml_str_credit_invoice).decode('UTF-8')
        })
        invoices = res.get('invoices', {})
        invoice = invoices.get(self.key_credit_invoice)
        self.assertTrue(invoice is not None, res)
        invoice = invoice.get('invoice_id', False)
        invoice = self.invoice_obj.browse(invoice)
        res = self.attach_wizard_obj.check_xml({
            self.key_credit_note: base64.b64encode(self.xml_str_credit_note).decode('UTF-8')
        })
        invoices = res.get('invoices', {})
        credit_note = invoices.get(self.key_credit_note)
        self.assertTrue(credit_note is not None, res)
        credit_note = credit_note.get('invoice_id', False)
        credit_note = self.invoice_obj.browse(credit_note)
        self.assertEqual(credit_note.reversed_entry_id.id, invoice.id)
        self.assertTrue(credit_note.id in invoice.reversal_move_id.ids)
