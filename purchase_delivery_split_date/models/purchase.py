# Copyright 2014-2016 Numérigraphe SARL
# Copyright 2017 Eficent Business and IT Consulting Services, S.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging
from itertools import groupby
from odoo import models, api, fields

_logger = logging.getLogger(__name__)


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    @api.model
    def _get_group_keys(self, order, line, picking=False):
        """Define the key that will be used to group. The key should be
        defined as a tuple of dictionaries, with each element containing a
        dictionary element with the field that you want to group by. This
        method is designed for extensibility, so that other modules can add
        additional keys or replace them by others."""
        date = line.date_planned.date()
        # Split date value to obtain only the attributes year, month and day
        key = (
            {'date_planned': fields.Date.to_string(date)},
        )
        return key

    @api.model
    def _first_picking_copy_vals(self, key, lines):
        """The data to be copied to new pickings is updated with data from the
        grouping key.  This method is designed for extensibility, so that
        other modules can store more data based on new keys."""
        vals = {'move_lines': []}
        for key_element in key:
            if 'date_planned' in key_element.keys():
                vals['date'] = key_element['date_planned']
        return vals

    @api.multi
    def _create_stock_moves(self, picking):
        """Group the receptions in one picking per group key"""
        moves = self.env['stock.move']
        # Group the order lines by group key
        order_lines = sorted(self, key=lambda l: l.date_planned)
        date_groups = groupby(order_lines, lambda l: self._get_group_keys(
            l.order_id, l, picking=picking))

        first_picking = False
        # If a picking is provided, use it for the first group only
        if picking:
            first_picking = picking
            key, lines = next(date_groups)
            po_lines = self.env['purchase.order.line']
            for line in list(lines):
                po_lines += line
            picking._update_picking_from_group_key(key)
            moves += super(PurchaseOrderLine, po_lines)._create_stock_moves(
                first_picking)

        for key, lines in date_groups:
            # If a picking is provided, clone it for each key for modularity
            if picking:
                copy_vals = self._first_picking_copy_vals(key, lines)
                picking = first_picking.copy(copy_vals)
            po_lines = self.env['purchase.order.line']
            for line in list(lines):
                po_lines += line
            moves += super(PurchaseOrderLine, po_lines)._create_stock_moves(
                picking)
        return moves


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    @api.multi
    def _update_picking_from_group_key(self, key):
        """The picking is updated with data from the grouping key.
        This method is designed for extensibility, so that other modules
        can store more data based on new keys."""
        for rec in self:
            for key_element in key:
                if 'date_planned' in key_element.keys():
                    rec.date = key_element['date_planned']
        return False
