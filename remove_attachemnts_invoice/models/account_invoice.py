from odoo import models, api, exceptions, _


class AccountMove(models.Model):
    _inherit = 'account.move'
    _description = "module to delete duplicate attachments when sent by email"

    # @api.multi
    def action_invoice_sent(self):
        """ Open a window to compose an email, with the edi invoice template
            message loaded by default
        """

        # self.ensure_one()
        template = self.env.ref('account.email_template_edi_invoice', False)
        compose_form = self.env.ref(
            'mail.email_compose_message_wizard_form', False)
        ctx = dict(
            default_model='account.move',
            default_res_id=self.id,
            default_use_template=bool(template),
            default_template_id=template and template.id or False,
            default_composition_mode='comment',
            mark_invoice_as_sent=True,
            custom_layout="account.mail_template_data_notification_email_account_invoice",
            force_email=True
        )

        # Begin modification
        name = ''
        band = False
        attachments = self.env['ir.attachment']
        attachs = attachments.search(
            [('res_model', '=', self._name), ('res_id', '=', self.id)])
        for attach in attachs:
            name = attach.name
            if name.upper()[:3] == 'FAC':
                if name[-3:] == 'xml':
                    if band == False:
                        band = True
                    else:
                        attachments.search([('id', '=', attach.id)]).unlink()
                else:
                    attachments.search([('id', '=', attach.id)]).unlink()
            elif name[-3:] == 'xml':
                if band == False:
                    band = True
                else:
                    attachments.search([('id', '=', attach.id)]).unlink()

        return {
            'name': _('Compose Email'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form.id, 'form')],
            'view_id': compose_form.id,
            'target': 'new',
            'context': ctx,
        }
