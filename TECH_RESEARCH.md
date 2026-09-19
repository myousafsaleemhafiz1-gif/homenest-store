# HomeNest Store — Admin UX Research Notes

Updated: 2026-09-16

## Research basis

The admin redesign follows current patterns documented by Shopify and WooCommerce rather than treating the back office as a generic dashboard.

- Shopify describes its admin as the central hub for orders, products, customers, analytics/reports, marketing/discounts and store settings. Its navigation uses a persistent sidebar and a global search entry point.
- WooCommerce groups store operations around Home, Orders, Products, Analytics, Marketing and Settings, and its Home screen surfaces actionable tasks, orders to fulfill and inventory to review.
- Shopify's current product analytics highlights sell-through, days of inventory remaining and inventory value, reinforcing that inventory needs to be an operational view rather than a decorative metric.
- WooCommerce customer analytics surfaces order count, total spend, average order value and customer activity, so the HomeNest admin keeps customer management as a first-class area.
- Baymard's recent ecommerce research emphasizes scannability, filtering and fast comparison for product lists and clear product-page usability for shoppers.

## Implemented structure

1. Persistent left navigation: Dashboard, Orders, Products, Inventory, Customers, Discounts, Store content, Security.
2. Global store search shortcut with `/` focus.
3. Dashboard is action-first: sales KPIs, order queue, inventory alerts, recent orders, top products and common store-management tasks.
4. Dense operational tables replace oversized decorative cards for order management.
5. Store-content control remains connected to existing settings so logo, homepage content, delivery and COD settings remain editable.
6. Product-management views keep local image uploads and the existing 4-image product gallery workflow.
7. Responsive behavior collapses the sidebar and tables for smaller screens.
8. Motion is purposeful and respects `prefers-reduced-motion`.

## Sources

- Shopify admin: https://help.shopify.com/en/manual/shopify-admin
- Shopify admin navigation: https://help.shopify.com/en/manual/shopify-admin/shopify-admin-overview
- Shopify analytics: https://help.shopify.com/en/manual/reports-and-analytics/shopify-reports/overview-dashboard
- Shopify product analytics: https://help.shopify.com/en/manual/products/analytics
- WooCommerce Home screen: https://woocommerce.com/document/home-screen/
- WooCommerce menu items: https://woocommerce.com/document/woocommerce-menu-items/
- WooCommerce settings: https://woocommerce.com/document/configuring-woocommerce-settings/
- WooCommerce customer analytics: https://woocommerce.com/document/customers-report/
- Baymard PLP research: https://baymard.com/blog/product-listing-page-plp-ux
- Baymard product page research: https://baymard.com/blog/current-state-ecommerce-product-page-ux


## Logo and gallery UX research (2026-09-17)

- Baymard: product image galleries should make additional images obvious and support detailed visual inspection; thumbnails provide stronger information scent than dots alone.
- Baymard: gallery overlays can be useful, but controls must avoid making images hard to enlarge or navigate.
- WooCommerce: a modern product gallery can combine thumbnails, a larger viewer, hover zoom, a full-screen popup, and previous/next navigation; touch gestures are supported on mobile.
- Shopify: product media uses a featured/main image plus additional media uploaded directly in product editing.

Implementation for HomeNest: four local product image fields, thumbnail navigation, hover inspection, full-screen lightbox, next/previous controls, wheel zoom, pan, double-click zoom, pinch-to-zoom and mobile swipe.


## 2026-09-18 COD + prepaid delivery-fee research

The requested payment model is a documented ecommerce pattern: customers can pay a deposit/partial amount when selecting Cash on Delivery, with the remaining balance collected on delivery. WooCommerce documents deposits/partial payments and a COD extension that supports charging the total shipping cost as the upfront deposit.

A Pakistan-facing example also publicly documents the exact split requested here: the delivery fee is paid online to confirm/dispatch a COD order, while the product price is paid in cash to the courier on arrival.

For the real gateway layer, HomeNest is wired for Safepay hosted checkout. Safepay's current public developer materials describe creating a payment token, generating a hosted checkout URL, redirecting the customer, and receiving payment events through webhooks. The webhook must be treated as the trusted confirmation channel in production.
