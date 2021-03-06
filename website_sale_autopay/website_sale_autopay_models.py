# -*- coding: utf-8 -*-
from odoo import fields, api
from odoo import models


class PaymentAcquirer(models.Model):
    _inherit = 'payment.acquirer'

    journal_id = fields.Many2one('account.journal', 'Payment method', help='This journal is used to auto pay invoice when online payment is received')

    @api.onchange('company_id')
    def _onchange_company_id(self):
        if self.company_id:
            return {'domain': {'journal_id': [('company_id', '=', self.company_id.id)]}}


class SaleOrder(models.Model):

    _inherit = 'sale.order'

    def action_confirm(self):
        super(SaleOrder, self).action_confirm(ids)
        r = self.browse(ids[0])
        if r.payment_tx_id and r.payment_tx_id.state == 'done' and r.payment_acquirer_id:
            r._autopay()

    def _autopay(self):
            # Keep old indent to don't touch git history
            r = self.browse(ids[0])

            sale_order_company = r.company_id
            user_company = self.env['res.users'].browse(uid).company_id
            self.env['res.users'].write(uid, {'company_id': sale_order_company.id})

            journal_id = r.payment_acquirer_id.journal_id.id or self.env['account.invoice'].default_get(['journal_id'])['journal_id']

            for m in r.order_line:
                m.qty_to_invoice = m.product_uom_qty

            res = r.pool['sale.order'].action_invoice_create([r.id], context)
            invoice_id = res[0]

            # [validate]
            invoice_obj = r.env['account.invoice'].browse(invoice_id)
            journal_obj = r.env['account.journal'].browse(journal_id)
            invoice_obj.signal_workflow('invoice_open')

            # [register payment]
            invoice_obj.pay_and_reconcile(journal_obj, invoice_obj.amount_total)
            invoice_obj.action_move_create()
            invoice_obj.confirm_paid()

            # return user company to its original value
            self.env['res.users'].write(uid, {'company_id': user_company.id})
