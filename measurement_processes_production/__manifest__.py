# -*- coding: utf-8 -*-

###################################################################################
#
#    This program is free software: you can modify
#    it under the terms of the GNU Affero General Public License (AGPL) as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
###################################################################################

{
    'name': 'Measurement of processes in production',
    'version': '12.0.0.0.1',
    'summary': 'Measurement of processes in production',
    'author': 'gflores',
    'maintainer': 'gflores',
    'company': 'Grupo Requiez SA de CV',
    'website': 'https://www.gruporequiez.com',
    'depends': ['stock', 'mrp'],
    'category': 'Inventory',
    'demo': [],
    'data': [
        'wizard/process_measurement_view.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'AGPL-3',
}
