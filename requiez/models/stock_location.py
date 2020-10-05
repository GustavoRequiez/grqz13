# Copyright 2018 Vauxoo (https://www.vauxoo.com) <info@vauxoo.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class Location(models.Model):
    _inherit = 'stock.location'

    default_location = fields.Boolean('Is the default location?',
                                      help="Check this box to allow the use \
                                      of this location as the default \
                                      location.")
