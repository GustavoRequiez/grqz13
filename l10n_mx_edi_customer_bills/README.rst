Mexican Localization to Attach CFDI(s) for Customer Invoices
============================================================

This module allow:

- Attach fiscal documents on customer invoices.
- Create new customer invoice based on a CFDI.

To allow this process are made some validations as:

- The amount in the CFDI is the same that the invoice total (when only attach)
- That the CFDI is not cancelled on the SAT system.
- The UUID is not attached in another documents
- The Folio in the CFDI is the same that the origin field in the invoice.
- That the CFDI has the attribute TipoDeComprobante = I.
- It's possible to avoid payment complement setting the system parameter
  'l10n_mx_edi.avoid_stamp_payments' (keep it void to stamp payments normally).

Only support CFDI on version 3.3

Installation
============

- This module depends on:

  No extra depends

You could install all the dependencies with pip:

pip install -r requirements.txt

- You need the `Vauxoo/Odoo <https://github.com/vauxoo/odoo/>`_ repo, because this have some improves in version 11.0

- And install as a regular Odoo module:

  - Download this module from `Vauxoo/mexico
    <https://git.vauxoo.com/vauxoo/mexico>`_
  - Add the repository folder into your odoo addons-path.
  - Go to ``Settings > Module list`` search for the current name and click in
    ``Install`` button.

Configuration
=============

To configure this module, you need to:

- Create the sale taxes (ISR, IVA, and IEPS). 
  
If the module ``l10n_mx`` is installed, it's not necessary to create the taxes.

Bug Tracker
===========

Bugs are tracked on
`GitHub Issues <https://git.vauxoo.com/Vauxoo/mexico/issues>`_.
In case of trouble, please check there if your issue has already been reported.
If you spotted it first, help us smashing it by providing a detailed and
welcomed feedback
`here <https://git.vauxoo.com/Vauxoo/mexico/issues/new?body=module:%20
l10n_mx_base%0Aversion:%20
8.0.2.0%0A%0A**Steps%20to%20reproduce**%0A-%20...%0A%0A**Current%20behavior**%0A%0A**Expected%20behavior**>`_

Credits
=======

**Contributors**

* Nhomar Hernandez <nhomar@vauxoo.com> (Planner/Auditor)
* Luis Torres <luis_t@vauxoo.com> (Developer)

Maintainer
==========

.. image:: https://s3.amazonaws.com/s3.vauxoo.com/description_logo.png
   :alt: Vauxoo
