# Copyright 2016 Antiun Ingenieria S.L. - Javier Iniesta
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models, _


class MrpProduction(models.Model):
    _inherit = "mrp.production"

    sale_id = fields.Many2one(
        comodel_name='sale.order', string='Sale order', readonly=True,
        store=True, related='procurement_group_id.sale_id')
    partner_id = fields.Many2one(
        comodel_name='res.partner', related='sale_id.partner_id',
        string='Customer', store=True)
    commitment_date = fields.Datetime(
        related='sale_id.commitment_date', string='Commitment Date',
        store=True)

    @api.model
    def create(self, values):
        if not values.get('procurement_group_id'):
            procurement_old = self.env['procurement.group'].search([('sale_id.name', '=', values['origin'])], limit=1, order='id ASC')
            values['procurement_group_id'] = self.env["procurement.group"].create({
                'name': values.get('name', 'PG'),
                'sale_id': procurement_old and procurement_old.sale_id.id,
            }).id
        production = super(MrpProduction, self).create(values)
        return production
