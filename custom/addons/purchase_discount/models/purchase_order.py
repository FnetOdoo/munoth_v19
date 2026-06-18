from odoo import api, fields, models
from odoo.exceptions import ValidationError


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    def _prepare_supplier_info(self, partner, line, price, currency):
        vals = super()._prepare_supplier_info(partner, line, price, currency)
        vals["discount"] = line.discount
        return vals


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    discount = fields.Float(
        string="Discount (%)",
        digits=(16, 2),  # ← Fixed: "Discount" precision may not exist in v19
        default=0.0,
    )

    _sql_constraints = [
        (
            "purchase_order_line_discount_limit",  # ← Fixed: more unique name
            "CHECK (discount >= 0.0 AND discount <= 100.0)",  # ← Fixed: also block negative
            "Discount must be between 0% and 100%.",
        )
    ]

    @api.constrains("discount")
    def _check_discount(self):
        for line in self:
            if line.discount < 0.0:
                raise ValidationError(
                    "Discount cannot be negative. Please enter a value between 0% and 100%."
                )
            if line.discount > 100.0:
                raise ValidationError(
                    "Discount cannot exceed 100%. Please enter a value between 0% and 100%."
                )

    # ─── Validates WHILE TYPING (instant UI feedback) ──────────
    @api.onchange("discount")
    def _onchange_discount(self):
        if self.discount and self.discount < 0.0:
            self.discount = 0.0
            return {
                "warning": {
                    "title": "Invalid Discount",
                    "message": "Discount cannot be negative. Value reset to 0%.",
                }
            }
        if self.discount and self.discount > 100.0:
            self.discount = 100.0
            return {
                "warning": {
                    "title": "Invalid Discount",
                    "message": "Discount cannot exceed 100%. Value reset to 100%.",
                }
            }

    def _auto_init(self):
        """Force apply SQL constraint on existing tables in v19"""
        super()._auto_init()

        # Step 1: Fix NULL and invalid values BEFORE adding constraint
        self.env.cr.execute("""
            -- Set NULL discounts to 0
            UPDATE purchase_order_line 
            SET discount = 0.0 
            WHERE discount IS NULL;

            -- Reset negative discounts to 0
            UPDATE purchase_order_line 
            SET discount = 0.0 
            WHERE discount < 0.0;

            -- Cap discounts over 100 to 100
            UPDATE purchase_order_line 
            SET discount = 100.0 
            WHERE discount > 100.0;
        """)

        # Step 2: Drop old constraint if exists (from failed attempts)
        self.env.cr.execute("""
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM pg_constraint
                    WHERE conname = 'purchase_order_line_discount_limit'
                    AND conrelid = 'purchase_order_line'::regclass
                ) THEN
                    ALTER TABLE purchase_order_line
                    DROP CONSTRAINT purchase_order_line_discount_limit;
                END IF;
            END;
            $$;
        """)

        # Step 3: Now safely add the constraint
        self.env.cr.execute("""
            DO $$
            BEGIN
                ALTER TABLE purchase_order_line
                ADD CONSTRAINT purchase_order_line_discount_limit
                CHECK (discount >= 0.0 AND discount <= 100.0);
            END;
            $$;
        """)
    # adding discount to depends
    @api.depends("discount")
    def _compute_amount(self):
        return super()._compute_amount()

    def _prepare_compute_all_values(self):
        vals = super()._prepare_compute_all_values()
        vals.update({"price_unit": self._get_discounted_price_unit()})
        return vals

    def _get_discounted_price_unit(self):
        self.ensure_one()
        if self.discount:
            return self.price_unit * (1 - self.discount / 100)
        return self.price_unit

    def _get_stock_move_price_unit(self):
        if hasattr(self.env, "ocb"):
            return super()._get_stock_move_price_unit()
        if self.env.context.get("skip_update_price_unit"):
            return super()._get_stock_move_price_unit()
        price_unit = False
        price = self._get_discounted_price_unit()
        if price != self.price_unit:
            price_unit = self.price_unit
            self.with_context(skip_update_price_unit=True).price_unit = price
        price = super()._get_stock_move_price_unit()
        if price_unit:
            self.with_context(skip_update_price_unit=True).price_unit = price_unit
        return price

    @api.onchange("product_qty", "product_uom_id")  # ← Fixed: v19 uses product_uom not product_uom_id
    def _onchange_quantity(self):
        """
        Check if a discount is defined into the supplier info and if so then
        apply it to the current purchase order line
        """
        res = None
        parent = super()
        if hasattr(parent, '_onchange_quantity'):
            res = parent._onchange_quantity()

        if self.product_id:
            date = None
            if self.order_id.date_order:
                date = self.order_id.date_order.date()
            seller = self.product_id._select_seller(
                partner_id=self.partner_id,
                quantity=self.product_qty,
                date=date,
                uom_id=self.product_uom_id,  # ← Fixed: match v19 field name
            )
            self._apply_value_from_seller(seller)
        return res

    @api.model
    def _apply_value_from_seller(self, seller):
        if not seller:
            # ← Fixed: simplified, always reset discount to 0 if no seller
            self.discount = 0.0
            return
        self.discount = seller.discount if seller.discount else 0.0

    def _prepare_account_move_line(self, move=False):
        vals = super()._prepare_account_move_line(move)
        vals["discount"] = self.discount
        return vals

    @api.model
    def _prepare_purchase_order_line(
        self, product_id, product_qty, product_uom_id, company_id, supplier, po
    ):
        res = super()._prepare_purchase_order_line(
            product_id, product_qty, product_uom_id, company_id, supplier, po
        )
        partner = supplier.name
        uom_po_qty = product_uom_id._compute_quantity(product_qty, product_id.uom_po_id)
        seller = product_id.with_company(company_id)._select_seller(
            partner_id=partner,
            quantity=uom_po_qty,
            date=po.date_order and po.date_order.date(),
            uom_id=product_id.uom_po_id,
        )
        res.update(self._prepare_purchase_order_line_from_seller(seller))
        return res

    @api.model
    def _prepare_purchase_order_line_from_seller(self, seller):
        if not seller:
            return {}
        return {"discount": seller.discount}