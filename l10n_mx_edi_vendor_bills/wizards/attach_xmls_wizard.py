# Copyright 2017, Jarsa Sistemas, S.A. de C.V.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import base64

from lxml import etree, objectify

from odoo import _, api, fields, models
from odoo.tools.float_utils import float_is_zero
from odoo.tools import float_round
from odoo.exceptions import UserError

TYPE_CFDI22_TO_CFDI33 = {
    'ingreso': 'I',
    'egreso': 'E',
    'traslado': 'T',
    'nomina': 'N',
    'pago': 'P',
}


class AttachXmlsWizard(models.TransientModel):
    _name = 'attach.xmls.wizard'
    _description = "Attach xmls"

    @api.model
    def _default_journal(self):
        type_inv = 'in_invoice' if self._context.get(
            'l10n_mx_edi_invoice_type') == 'in' else 'out_invoice'
        return self.env['account.move'].with_context(
            default_type=type_inv)._get_default_journal()

    @api.model
    def _get_journal_domain(self):
        type_inv = 'purchase' if self._context.get(
            'l10n_mx_edi_invoice_type') == 'in' else 'sale'
        return [('type', '=', type_inv)]

    @api.model
    def _get_account_domain(self):
        return [('company_id', '=', self.env.company.id)]

    dragndrop = fields.Char()
    account_id = fields.Many2one(
        'account.account',
        help='Optional field to define the account that will be used in all '
        'the lines of the invoice.\nIf the field is not set, the wizard will '
        'take the account by default.',
        domain=_get_account_domain,
    )
    journal_id = fields.Many2one(
        'account.journal', required=True,
        default=_default_journal,
        domain=_get_journal_domain,
        help='This journal will be used in the invoices generated with this '
        'wizard.')
    omit_cfdi_related = fields.Boolean(
        help='Use this option when the CFDI attached do not have a CFDI '
        'related and is a Refund (Only as exception)')

    @staticmethod
    def _xml2capitalize(xml):
        """Receive 1 lxml etree object and change all attrib to Capitalize.
        """
        def recursive_lxml(element):
            for attrib, value in element.attrib.items():
                new_attrib = "%s%s" % (attrib[0].upper(), attrib[1:])
                element.attrib.update({new_attrib: value})

            for child in element.getchildren():
                child = recursive_lxml(child)
            return element
        return recursive_lxml(xml)

    @staticmethod
    def _l10n_mx_edi_convert_cfdi32_to_cfdi33(xml):
        """Convert a xml from cfdi32 to cfdi33
        :param xml: The xml 32 in lxml.objectify object
        :return: A xml 33 in lxml.objectify object
        """
        if xml.get('version', None) != '3.2' or xml.get(
                'Version', None) == '3.3':
            return xml
        # TODO: Process negative taxes "Retenciones" node
        # TODO: Process payment term
        xml = AttachXmlsWizard._xml2capitalize(xml)
        xml.attrib.update({
            'TipoDeComprobante': TYPE_CFDI22_TO_CFDI33[
                xml.attrib['TipoDeComprobante']],
            'Version': '3.3',
            # By default creates Payment Complement since that the imported
            # invoices are most imported for this propose if it is not the case
            # then modified manually from odoo.
            'MetodoPago': 'PPD',
        })
        return xml

    @staticmethod
    def collect_taxes(taxes_xml):
        """ Get tax data of the Impuesto node of the xml and return
        dictionary with taxes datas
        :param taxes_xml: Impuesto node of xml
        :type taxes_xml: etree
        :return: A list with the taxes data
        :rtype: list
        """
        taxes = []
        tax_codes = {'001': 'ISR', '002': 'IVA', '003': 'IEPS'}
        for rec in taxes_xml:
            tax_xml = rec.get('Impuesto', '')
            tax_xml = tax_codes.get(tax_xml, tax_xml)
            amount_xml = float(rec.get('Importe', '0.0'))
            rate_xml = float_round(
                float(rec.get('TasaOCuota', '0.0')) * 100, 4)
            if 'Retenciones' in rec.getparent().tag:
                amount_xml = amount_xml * -1
                rate_xml = rate_xml * -1

            taxes.append({'rate': rate_xml, 'tax': tax_xml,
                          'amount': amount_xml})
        return taxes

    def get_impuestos(self, xml):
        if not hasattr(xml, 'Impuestos'):
            return {}
        taxes_list = {'wrong_taxes': [], 'taxes_ids': {}, 'withno_account': []}
        taxes = []
        for index, rec in enumerate(xml.Conceptos.Concepto):
            if not hasattr(rec, 'Impuestos'):
                continue
            taxes_list['taxes_ids'][index] = []
            taxes_xml = rec.Impuestos
            if hasattr(taxes_xml, 'Traslados'):
                taxes = self.collect_taxes(taxes_xml.Traslados.Traslado)
            if hasattr(taxes_xml, 'Retenciones'):
                taxes += self.collect_taxes(taxes_xml.Retenciones.Retencion)

            for tax in taxes:
                tax_group_id = self.env['account.tax.group'].search(
                    [('name', 'ilike', tax['tax'])])
                domain = [('tax_group_id', 'in', tax_group_id.ids),
                          ('type_tax_use', '=', 'purchase'), ]
                if -10.67 <= tax['rate'] <= -10.66:
                    domain.append(('amount', '<=', -10.66))
                    domain.append(('amount', '>=', -10.67))
                else:
                    domain.append(('amount', '=', tax['rate']))

                name = '%s(%s%%)' % (tax['tax'], tax['rate'])

                tax_get = self.env['account.tax'].search(domain, limit=1)
                taxes_to_omit = self.get_taxes_to_omit()

                if (not tax_group_id or not tax_get) and tax.get('tax', False) not in taxes_to_omit:
                    taxes_list['wrong_taxes'].append(name)
                    continue
                # TODO review if this validation of account in taxes is correct
                tax_account = tax_get.invoice_repartition_line_ids.filtered(
                    lambda rec: rec.repartition_type == 'tax')
                if not tax_account and tax.get('tax', '') not in taxes_to_omit:
                    taxes_list['withno_account'].append(
                        name if name else tax['tax'])
                else:
                    tax['id'] = tax_get.id
                    tax['account'] = tax_account.id
                    tax['name'] = name if name else tax['tax']
                    tax['for_expenses'] = not bool(tax_get)
                    taxes_list['taxes_ids'][index].append(tax)
        return taxes_list

    def get_local_taxes(self, xml):
        if not hasattr(xml, 'Complemento'):
            return {}
        type_tax_use = 'purchase' if self._context.get(
            'l10n_mx_edi_invoice_type') == 'in' else 'sale'
        local_taxes = xml.Complemento.xpath(
            'implocal:ImpuestosLocales',
            namespaces={'implocal': 'http://www.sat.gob.mx/implocal'})
        taxes_list = {
            'wrong_taxes': [], 'withno_account': [], 'taxes': []}
        if not local_taxes:
            return taxes_list
        local_taxes = local_taxes[0]
        tax_obj = self.env['account.tax']
        taxes_to_omit = self.get_taxes_to_omit()
        if hasattr(local_taxes, 'RetencionesLocales'):
            for local_ret in local_taxes.RetencionesLocales:
                name = local_ret.get('ImpLocRetenido')
                tasa = float(local_ret.get('TasadeRetencion')) * -1
                tax = tax_obj.search([
                    '&',
                    ('type_tax_use', '=', type_tax_use),
                    '|',
                    ('name', '=', name),
                    ('amount', '=', tasa)], limit=1)
                if not tax and name not in taxes_to_omit:
                    taxes_list['wrong_taxes'].append(name)
                    continue
                tax_account = tax.invoice_repartition_line_ids.filtered(lambda rec: rec.repartition_type == 'tax')
                if not tax_account and name not in taxes_to_omit:
                    taxes_list['withno_account'].append(name)
                    continue
                taxes_list['taxes'].append((0, 0, {
                    'tax_id': tax.id,
                    'account_id': tax_account.id,
                    'name': name,
                    'amount': float(local_ret.get('Importe')) * -1,
                    'for_expenses': not bool(tax),
                }))
        if hasattr(local_taxes, 'TrasladosLocales'):
            for local_tras in local_taxes.TrasladosLocales:
                name = local_tras.get('ImpLocTrasladado')
                tasa = float(local_tras.get('TasadeTraslado'))
                tax = tax_obj.search([
                    '&',
                    ('type_tax_use', '=', type_tax_use),
                    '|',
                    ('name', '=', name),
                    ('amount', '=', tasa)], limit=1)
                if not tax and name not in taxes_to_omit:
                    taxes_list['wrong_taxes'].append(name)
                    continue
                tax_account = tax.invoice_repartition_line_ids.filtered(lambda rec: rec.repartition_type == 'tax')
                if not tax_account and name not in taxes_to_omit:
                    taxes_list['withno_account'].append(name)
                    continue
                taxes_list['taxes'].append((0, 0, {
                    'tax_id': tax.id,
                    'account_id': tax_account.id,
                    'name': name,
                    'amount': float(local_tras.get('Importe')),
                    'for_expenses': not bool(tax),
                }))

        return taxes_list

    def get_xml_folio(self, xml):
        return '%s%s' % (xml.get('Serie', ''), xml.get('Folio', ''))

    def validate_documents(self, key, xml, account_id):
        """ Validate the incoming or outcoming document before create or
        attach the xml to invoice
        :param key: Name of the document that is being validated
        :type key: str
        :param xml: xml file with the datas of purchase
        :type xml: etree
        :param account_id: The account by default that must be used in the
            lines of the invoice if this is created
        :type account_id: int
        :return: Result of the validation of the CFDI and the invoices created.
        :rtype: dict
        """
        wrongfiles = {}
        invoices = {}
        inv_obj = self.env['account.move']
        partner_obj = self.env['res.partner']
        currency_obj = self.env['res.currency']
        inv = inv_obj
        inv_id = False
        xml_str = etree.tostring(xml, pretty_print=True, encoding='UTF-8')
        xml_vat_emitter, xml_vat_receiver, xml_amount, xml_currency, version,\
            xml_name_supplier, xml_type_of_document, xml_uuid, xml_serie_folio,\
            xml_taxes = self._get_xml_data(xml)
        xml_related_uuid = related_invoice = False
        exist_supplier = partner_obj.search(
            ['&', ('vat', '=', xml_vat_emitter), '|',
             ('company_id', '=', False),
             ('company_id', '=', self.env.company.id)], limit=1)
        xml_folio = xml.get('Folio', '')
        invoice = self._search_invoice(exist_supplier, xml_amount, xml_serie_folio, xml_folio)
        exist_reference = invoice if invoice and xml_uuid != invoice.l10n_mx_edi_cfdi_uuid else False  # noqa
        if exist_reference and not exist_reference.l10n_mx_edi_cfdi_uuid:
            inv = exist_reference
            inv_id = inv.id
            exist_reference = False
            inv.l10n_mx_edi_update_sat_status()
        xml_status = inv.l10n_mx_edi_sat_status
        inv_vat_receiver = (
            self.env.company.vat or '').upper()
        inv_vat_emitter = (
            inv and inv.commercial_partner_id.vat or '').upper()
        inv_amount = inv.amount_total
        inv_folio = inv.invoice_payment_ref or ''
        domain = [('l10n_mx_edi_cfdi_name', '!=', False)]
        if exist_supplier:
            domain += [('partner_id', 'child_of', exist_supplier.id)]
        if xml_type_of_document == 'I':
            domain += [('type', '=', 'in_invoice')]
        if xml_type_of_document == 'E':
            domain += [('type', '=', 'in_refund')]
        uuid_dupli = xml_uuid in inv_obj.search(domain).mapped(
            'l10n_mx_edi_cfdi_uuid')
        mxns = [
            'mxp', 'mxn', 'pesos', 'peso mexicano', 'pesos mexicanos', 'mn']
        xml_currency = 'MXN' if xml_currency.lower(
        ) in mxns else xml_currency

        exist_currency = currency_obj.search(
            [('name', '=', xml_currency)], limit=1)
        xml_related_uuid = False
        if xml_type_of_document == 'E' and hasattr(xml, 'CfdiRelacionados'):
            xml_related_uuid = xml.CfdiRelacionados.CfdiRelacionado.get('UUID')
            related_invoice = xml_related_uuid in inv_obj.search([
                ('l10n_mx_edi_cfdi_name', '!=', False),
                ('type', '=', 'in_invoice')]).mapped('l10n_mx_edi_cfdi_uuid')
        omit_cfdi_related = self._context.get('omit_cfdi_related')
        force_save = False
        if self.env.user.has_group(
                'l10n_mx_edi_vendor_bills.allow_force_invoice_generation'):
            force_save = self._context.get('force_save')
        errors = [
            (not xml_uuid, {'signed': True}),
            (xml_status == 'cancelled', {'cancel': True}),
            ((xml_uuid and uuid_dupli), {'uuid_duplicate': xml_uuid}),
            ((inv_vat_receiver != xml_vat_receiver),
             {'rfc': (xml_vat_receiver, inv_vat_receiver)}),
            ((not inv_id and exist_reference),
             {'invoice_payment_ref': (xml_name_supplier, xml_serie_folio)}),
            (version != '3.3', {'version': True}),
            ((not inv_id and not exist_supplier),
             {'supplier': xml_name_supplier}),
            ((not inv_id and xml_currency and not exist_currency),
             {'currency': xml_currency}),
            ((not inv_id and xml_taxes.get('wrong_taxes', False)),
             {'taxes': xml_taxes.get('wrong_taxes', False)}),
            ((not inv_id and xml_taxes.get('withno_account', False)),
             {'taxes_wn_accounts': xml_taxes.get(
                 'withno_account', False)}),
            ((inv_id and inv_folio not in [xml_serie_folio, xml_folio]),
             {'folio': (xml_serie_folio, inv_folio)}),
            ((inv_id and inv_vat_emitter != xml_vat_emitter), {
                'rfc_supplier': (xml_vat_emitter, inv_vat_emitter)}),
            ((inv_id and not float_is_zero(
                float(inv_amount) - xml_amount, precision_digits=2)),
                {'amount': (xml_amount, inv_amount)}),
            ((xml_related_uuid and not related_invoice and not force_save),
             {'invoice_not_found': xml_related_uuid}),
            ((not omit_cfdi_related and xml_type_of_document == 'E' and
              not xml_related_uuid), {'no_xml_related_uuid': True}),
        ]
        msg = {}
        for error in errors:
            if error[0]:
                msg.update(error[1])
        if msg:
            msg.update({'xml64': True})
            wrongfiles.update({key: msg})
            return {'wrongfiles': wrongfiles, 'invoices': invoices}

        if not inv_id:
            invoice_status = self.create_invoice(
                xml, exist_supplier, exist_currency,
                xml_taxes.get('taxes_ids', {}), account_id)

            if invoice_status['key'] is False:
                del invoice_status['key']
                invoice_status.update({'xml64': True})
                wrongfiles.update({key: invoice_status})
                return {'wrongfiles': wrongfiles, 'invoices': invoices}

            del invoice_status['key']
            invoices.update({key: invoice_status})
            return {'wrongfiles': wrongfiles, 'invoices': invoices}

        inv.l10n_mx_edi_cfdi = xml_str.decode('UTF-8')
        inv.generate_xml_attachment()
        inv.invoice_payment_ref = '%s|%s' % (xml_serie_folio, xml_uuid.split('-')[0])
        invoices.update({key: {'invoice_id': inv.id}})
        if not float_is_zero(float(inv.amount_total) - xml_amount,
                             precision_digits=0):
            inv.message_post(
                body=_('The XML attached total amount is different to '
                       'the total amount in this invoice. The XML total '
                       'amount is %s') % xml_amount)
        return {'wrongfiles': wrongfiles, 'invoices': invoices}

    @api.model
    def _get_xml_data(self, xml):
        """Return data from XML"""
        inv_obj = self.env['account.move']
        vat_emitter = xml.Emisor.get('Rfc', '').upper()
        vat_receiver = xml.Receptor.get('Rfc', '').upper()
        amount = float(xml.get('Total', 0.0))
        currency = xml.get('Moneda', 'MXN')
        version = xml.get('Version', xml.get('version'))
        name_supplier = xml.Emisor.get('Nombre', '')
        document_type = xml.get('TipoDeComprobante', False)
        tfd = inv_obj.l10n_mx_edi_get_tfd_etree(xml)
        uuid = False if tfd is None else tfd.get('UUID', '')
        folio = self.get_xml_folio(xml)
        taxes = self.get_impuestos(xml)
        local_taxes = self.get_local_taxes(xml)
        taxes['wrong_taxes'] = taxes.get(
            'wrong_taxes', []) + local_taxes.get('wrong_taxes', [])
        taxes['withno_account'] = taxes.get(
            'withno_account', []) + local_taxes.get('withno_account', [])
        return vat_emitter, vat_receiver, amount, currency, version,\
            name_supplier, document_type, uuid, folio, taxes

    def _search_invoice(self, exist_supplier, amount, serie_folio, folio):
        inv_obj = self.env['account.move']
        domain = [
            '|', ('partner_id', 'child_of', exist_supplier.id),
            ('partner_id', '=', exist_supplier.id)]
        force_folio = self.env['ir.config_parameter'].sudo().get_param(
            'l10n_mx_force_only_folio', '')
        if serie_folio and force_folio:
            domain.append('|')
            domain.append(('invoice_payment_ref', '=ilike', folio))
        if serie_folio:
            domain.append(('invoice_payment_ref', '=ilike', serie_folio))
            return inv_obj.search(domain, limit=1)
        domain.append(('amount_total', '>=', amount - 1))
        domain.append(('amount_total', '<=', amount + 1))
        domain.append(('l10n_mx_edi_cfdi_name', '=', False))
        domain.append(('state', '!=', 'cancel'))
        return inv_obj.search(domain, limit=1)

    @api.model
    def check_xml(self, files, account_id=False):
        """ Validate that attributes in the xml before create invoice
        or attach xml in it
        :param files: dictionary of CFDIs in b64
        :type files: dict
        param account_id: The account by default that must be used in the
        lines of the invoice if this is created
        :type account_id: int
        :return: the Result of the CFDI validation
        :rtype: dict
        """
        if not isinstance(files, dict):
            raise UserError(_("Something went wrong. The parameter for XML "
                              "files must be a dictionary."))
        wrongfiles = {}
        invoices = {}
        outgoing_docs = {}
        account_id = account_id or self._context.get('account_id', False)
        for key, xml64 in files.items():
            try:
                if isinstance(xml64, bytes):
                    xml64 = xml64.decode()
                xml_str = base64.b64decode(xml64.replace(
                    'data:text/xml;base64,', ''))
                # Fix the CFDIs emitted by the SAT
                xml_str = xml_str.replace(
                    b'xmlns:schemaLocation', b'xsi:schemaLocation')
                xml = objectify.fromstring(xml_str)
            except (AttributeError, SyntaxError) as exce:
                wrongfiles.update({key: {
                    'xml64': xml64, 'where': 'CheckXML',
                    'error': [exce.__class__.__name__, str(exce)]}})
                continue
            xml = self._l10n_mx_edi_convert_cfdi32_to_cfdi33(xml)
            if xml.get('TipoDeComprobante', False) == 'E':
                outgoing_docs.update({key: {'xml': xml, 'xml64': xml64}})
                continue
            if xml.get('TipoDeComprobante', False) != 'I':
                wrongfiles.update({key: {'cfdi_type': True, 'xml64': xml64}})
                continue
            # Check the incoming documents
            validated_documents = self.validate_documents(key, xml, account_id)
            wrongfiles.update(validated_documents.get('wrongfiles'))
            if wrongfiles.get(key, False) and \
                    wrongfiles[key].get('xml64', False):
                wrongfiles[key]['xml64'] = xml64
            invoices.update(validated_documents.get('invoices'))
        # Check the outgoing documents
        for key, value in outgoing_docs.items():
            xml64 = value.get('xml64')
            xml = value.get('xml')
            xml = self._l10n_mx_edi_convert_cfdi32_to_cfdi33(xml)
            validated_documents = self.validate_documents(key, xml, account_id)
            wrongfiles.update(validated_documents.get('wrongfiles'))
            if wrongfiles.get(key, False) and \
                    wrongfiles[key].get('xml64', False):
                wrongfiles[key]['xml64'] = xml64
            invoices.update(validated_documents.get('invoices'))
        return {'wrongfiles': wrongfiles,
                'invoices': invoices}

    def get_default_analytic(self, product, supplier):
        try:
            analytic_default = self.env['account.analytic.default']
        except BaseException:
            return False
        default_analytic = (
            analytic_default.account_get(
                product.id, supplier.id, self.env.user.id,
                fields.Date.today(), self.env.company.id) or False)
        return default_analytic

    def create_invoice(
            self, xml, supplier, currency_id, taxes, account_id=False):
        """ Create supplier invoice from xml file
        :param xml: xml file with the datas of purchase
        :type xml: etree
        :param supplier: supplier partner
        :type supplier: res.partner
        :param currency_id: payment currency of the purchase
        :type currency_id: res.currency
        :param taxes: Datas of taxes
        :type taxes: list
        :param account_id: The account by default that must be used in the
            lines, if this is defined will to use this.
        :type account_id: int
        :return: the Result of the invoice creation
        :rtype: dict
        """
        inv_obj = self.env['account.move']
        line_obj = self.env['account.move.line']
        prod_obj = self.env['product.product']
        prod_supplier_obj = self.env['product.supplierinfo']
        sat_code_obj = self.env['l10n_mx_edi.product.sat.code']
        uom_obj = uom_obj = self.env['uom.uom']
        xml_type_doc = xml.get('TipoDeComprobante', False)
        type_invoice = 'in_invoice' if xml_type_doc == 'I' else 'in_refund'
        journal = self._context.get('journal_id', False)
        journal = self.env['account.journal'].browse(
            journal) if journal else inv_obj.with_context(
                default_type=type_invoice)._get_default_journal()
        account_id = account_id or line_obj.with_context({
            'journal_id': journal.id, 'type': 'in_invoice'})._default_account()
        invoice_line_ids = []
        msg = (_('Some products are not found in the system, and the account '
                 'that is used like default is not configured in the journal, '
                 'please set default account in the journal '
                 '"%s" to create the invoice.') % journal.name)

        date_inv = xml.get('Fecha', '').split('T')

        for idx, rec in enumerate(xml.Conceptos.Concepto):
            name = rec.get('Descripcion', '')
            no_id = rec.get('NoIdentificacion', name)
            product_code = rec.get('ClaveProdServ', '')
            uom = rec.get('Unidad', '')
            uom_code = rec.get('ClaveUnidad', '')
            quantity = rec.get('Cantidad', '')
            price = rec.get('ValorUnitario', '')
            amount = float(rec.get('Importe', '0.0'))
            supplierinfo_id = prod_supplier_obj.search([
                ('name', '=', supplier.id),
                '|', ('product_name', '=ilike', name),
                ('product_code', '=ilike', no_id)], limit=1)
            product_id = supplierinfo_id.product_tmpl_id.product_variant_id
            product_id = product_id or prod_obj.search([
                '|', ('default_code', '=ilike', no_id),
                ('name', '=ilike', name)], limit=1)
            account_id = (
                account_id or product_id.property_account_expense_id.id or
                product_id.categ_id.property_account_expense_categ_id.id)

            if not account_id:
                return {
                    'key': False, 'where': 'CreateInvoice',
                    'error': [
                        _('Account to set in the lines not found.<br/>'), msg]}

            discount = 0.0
            if rec.get('Descuento') and amount:
                discount = (float(rec.get('Descuento', '0.0')) / amount) * 100

            domain_uom = [('name', '=ilike', uom)]
            line_taxes = taxes.get(idx, [])
            taxes_for_expenses = [
                line_taxes.pop(line_taxes.index(tax))
                for tax in line_taxes
                if tax.get('for_expenses')
            ]
            invoice_line_ids.extend([(0, 0, {
                'account_id': account_id,
                'name': tax.get('name'),
                'quantity': 1,
                'price_unit': tax.get('amount'),
            }) for tax in taxes_for_expenses])

            line_tax_ids = [tax['id'] for tax in taxes.get(idx, [])]
            code_sat = sat_code_obj.search([('code', '=', uom_code)], limit=1)
            domain_uom = [('l10n_mx_edi_code_sat_id', '=', code_sat.id)]
            uom_id = uom_obj.with_context(
                lang='es_MX').search(domain_uom, limit=1)

            if product_code in self._get_fuel_codes():
                tax = taxes.get(idx)[0] if taxes.get(idx, []) else {}
                quantity = 1.0
                price = tax.get('amount') / (tax.get('rate') / 100)
                invoice_line_ids.append((0, 0, {
                    'account_id': account_id,
                    'name': _('FUEL - IEPS'),
                    'quantity': quantity,
                    'product_uom_id': uom_id.id,
                    'price_unit': float(rec.get('Importe', 0)) - price,
                }))
            default_analytic = self.get_default_analytic(product_id, supplier)
            invoice_line_ids.append((0, 0, {
                'product_id': product_id.id,
                'account_id': account_id,
                'analytic_account_id':
                default_analytic.analytic_id.id if default_analytic else False,
                'name': name,
                'quantity': float(quantity),
                'product_uom_id': uom_id.id,
                'tax_ids': [(6, 0, line_tax_ids)],
                'price_unit': float(price),
                'discount': discount,
            }))

        xml_str = etree.tostring(xml, pretty_print=True, encoding='UTF-8')
        payment_method_id = self.env['l10n_mx_edi.payment.method'].search(
            [('code', '=', xml.get('FormaPago'))], limit=1)
        payment_condition = xml.get('CondicionesDePago') or False
        acc_pay_term = self.env['account.payment.term']
        if payment_condition:
            acc_pay_term = acc_pay_term.search([
                ('name', '=', payment_condition)], limit=1)
        xml_tfd = inv_obj.l10n_mx_edi_get_tfd_etree(xml)
        uuid = False if xml_tfd is None else xml_tfd.get('UUID', '')
        invoice_id = inv_obj.create({
            'partner_id': supplier.id,
            'invoice_payment_ref': '%s|%s' % (
                self.get_xml_folio(xml),
                uuid.split('-')[0]),
            'invoice_payment_term_id': acc_pay_term.id,
            'l10n_mx_edi_payment_method_id': payment_method_id.id,
            'l10n_mx_edi_usage': xml.Receptor.get('UsoCFDI'),
            'invoice_date': date_inv[0],
            'currency_id': (
                currency_id.id or self.env.company.currency_id.id),
            'invoice_line_ids': invoice_line_ids,
            'type': type_invoice,
            'l10n_mx_edi_time_invoice': date_inv[1],
            'journal_id': journal.id,
        })

        local_taxes = self.get_local_taxes(xml).get('taxes', [])
        if local_taxes:
            invoice_id.write({
                'invoice_line_ids': [(0, 0, {
                    'account_id': account_id,
                    'name': tax[-1]['name'],
                    'quantity': 1,
                    'price_unit': tax[-1]['amount'],
                }) for tax in local_taxes if tax[-1].get('for_expenses')],
            })
        if xml.get('version') == '3.2':
            # Global tax used for each line since that a manual tax line
            # won't have base amount assigned.
            tax_path = '//cfdi:Impuestos/cfdi:Traslados/cfdi:Traslado'
            tax_obj = self.env['account.tax']
            for global_tax in xml.xpath(tax_path, namespaces=xml.nsmap):
                tax_name = global_tax.attrib.get('impuesto')
                tax_percent = float(global_tax.attrib.get('tasa'))
                tax_group_id = self.env['account.tax.group'].search(
                    [('name', 'ilike', tax_name)])
                tax_domain = [
                    ('type_tax_use', '=', 'purchase'),
                    ('company_id', '=', self.env.company.id),
                    ('tax_group_id', 'in', tax_group_id.ids),
                    ('amount_type', '=', 'percent'),
                    ('amount', '=', tax_percent),
                ]
                tax = tax_obj.search(tax_domain, limit=1)
                if not tax:
                    return {
                        'key': False,
                        'taxes': ['%s(%s%%)' % (tax_name, tax_percent)],
                    }
                invoice_id.invoice_line_ids.write({
                    'invoice_line_tax_ids': [(4, tax.id)]})

            # Global discount used for each line
            # Decimal rounding wrong values could be imported will fix manually
            discount_amount = float(xml.attrib.get('Descuento', 0))
            sub_total_amount = float(xml.attrib.get('subTotal', 0))
            if discount_amount and sub_total_amount:
                percent = discount_amount * 100 / sub_total_amount
                invoice_id.invoice_line_ids.write({'discount': percent})

        invoice_id.l10n_mx_edi_cfdi = xml_str.decode('UTF-8')
        invoice_id.generate_xml_attachment()
        if xml_type_doc == 'E' and hasattr(xml, 'CfdiRelacionados'):
            xml_related_uuid = xml.CfdiRelacionados.CfdiRelacionado.get('UUID')
            invoice_id._set_cfdi_origin('01', [xml_related_uuid])
            related_invoices = inv_obj.search([
                ('partner_id', '=', supplier.id), ('type', '=', 'in_invoice')])
            related_invoices = related_invoices.filtered(
                lambda inv: inv.l10n_mx_edi_cfdi_uuid == xml_related_uuid)
            related_invoices.write({
                'reversal_move_id': [(4, invoice_id.id, 0)]
            })
        invoice_id.l10n_mx_edi_update_sat_status()
        return {'key': True, 'invoice_id': invoice_id.id}

    @api.model
    def create_partner(self, xml64, key):
        """ It creates the supplier dictionary, getting data from the XML
        Receives an xml decode to read and returns a dictionary with data """
        # Default Mexico because only in Mexico are emitted CFDIs
        try:
            if isinstance(xml64, bytes):
                xml64 = xml64.decode()
            xml_str = base64.b64decode(xml64.replace(
                'data:text/xml;base64,', ''))
            # Fix the CFDIs emitted by the SAT
            xml_str = xml_str.replace(
                b'xmlns:schemaLocation', b'xsi:schemaLocation')
            xml = objectify.fromstring(xml_str)
        except BaseException as exce:
            return {
                key: False, 'xml64': xml64, 'where': 'CreatePartner',
                'error': [exce.__class__.__name__, str(exce)]}

        xml = self._l10n_mx_edi_convert_cfdi32_to_cfdi33(xml)
        rfc_emitter = xml.Emisor.get('Rfc', False)
        name = xml.Emisor.get('Nombre', rfc_emitter)

        # check if the partner exist from a previos invoice creation
        partner = self.env['res.partner'].search([
            '&', ('name', '=', name), ('vat', '=', rfc_emitter), '|',
            ('company_id', '=', False),
            ('company_id', '=', self.env.company.id)])
        if partner:
            return partner

        partner = self.env['res.partner'].sudo().create({
            'name': name,
            'company_type': 'company',
            'vat': rfc_emitter,
            'country_id': self.env.ref('base.mx').id,
            'company_id': self.env.company.id,
        })
        msg = _('This partner was created when invoice %s%s was added from '
                'a XML file. Please verify that the datas of partner are '
                'correct.') % (xml.get('Serie', ''), xml.get('Folio', ''))
        partner.message_post(subject=_('Info'), body=msg)
        return partner

    @api.model
    def _get_fuel_codes(self):
        """Return the codes that could be used in FUEL"""
        fuel_codes = [str(r) for r in range(15101500, 15101516)]
        fuel_codes.extend(self.env.company.l10n_mx_edi_fuel_code_sat_ids.mapped('code'))
        return fuel_codes

    def get_taxes_to_omit(self):
        """Some taxes are not found in the system, but is correct, because that
        taxes should be adds in the invoice like expenses.
        To make dynamic this, could be add an system parameter with the name:
            l10n_mx_taxes_for_expense, and un the value set the taxes name,
        and if are many taxes, split the names by ','"""
        taxes = self.env['ir.config_parameter'].sudo().get_param(
            'l10n_mx_taxes_for_expense', '')
        return taxes.split(',')

    @api.model
    def _get_product_line(self, domain):
        return self.env['product.product'].sudo().with_context(
            force_company=self.env.company.id).search(domain, limit=1)
