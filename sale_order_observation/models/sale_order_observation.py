from odoo import fields, models


class SaleOrderObservation(models.AbstractModel):
    _name = 'sale.order.observation'

    observation = fields.Text()
    sale_line_observation = fields.Text(
        string='Observation',
        compute='_compute_observation',
        readonly=True)

    def _compute_observation(self):
        pass
