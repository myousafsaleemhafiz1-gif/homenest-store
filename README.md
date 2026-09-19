# HomeNest Store — Pro Full-Stack Ecommerce

A production-structured Flask + SQLAlchemy ecommerce store for local development, with a premium responsive storefront and a full operations-focused admin control center.

## Storefront
- Responsive premium storefront
- Product search, categories and sorting
- Product detail pages
- Session cart with quantity controls
- Guest checkout + customer accounts
- Coupon code support (`WELCOME10` seed coupon)
- Cash on Delivery checkout
- Order creation and automatic stock deduction
- Customer order history

## Admin Control Center
- Dashboard with revenue, order backlog, average order value and catalog health
- 7/30/90-day revenue view
- Sales trend visualization
- Recent order queue
- Low-stock and out-of-stock watchlist
- Product create/edit/hide/delete
- Product search and category/stock filters
- Quick stock adjustments (+5 / -5)
- Order search and status filters
- Full order detail view with customer, delivery, payment, items and totals
- Order workflow: Pending → Processing → Shipped → Delivered / Cancelled
- Customer directory with lifetime spend and order history
- Coupon creation, pause/activate and delete
- Store settings for business/support/delivery defaults
- Admin password change screen
- CSV exports for orders, products and customers
- Local admin activity log for important admin actions

## Security foundation
- Server-side admin authorization
- CSRF protection for state-changing requests
- Password hashing through Werkzeug
- HttpOnly + SameSite session-cookie configuration
- No authentication tokens stored in browser localStorage
- Production note: enable Secure cookies and HTTPS before public deployment

## Run on Windows
1. Extract the ZIP.
2. Open Command Prompt in the extracted `HomeNest_Store` folder.
3. Run `setup.bat`.
4. After setup, run `run.bat`.
5. Open `http://127.0.0.1:5000`.

### Admin
- URL: `http://127.0.0.1:5000/admin/login`
- Username: `admin`
- Default development password: `admin12345`

Immediately change the admin password from **Admin → Security** before any real deployment.

## Project files
- `app.py` — Flask application, database models and routes
- `templates/` — storefront and admin views
- `static/css/app.css` — storefront styling
- `static/css/admin.css` — admin dashboard styling
- `static/js/app.js` — storefront interactions
- `.env ` — environment configuration template
- `TECH_RESEARCH.md` — admin research/design notes

## Production note
The app is structured around Waitress for the provided local run command. Public deployment should also use HTTPS, a real secret key, a real admin password, real business contact details and a production database/storage setup.


## New retail-admin controls
- Product images and store logo upload directly from the admin computer; no image URL is required.
- Store name, logo, homepage hero image/content, delivery fee, free-shipping threshold, COD switch and footer messaging are editable from Store Settings.
- Each product supports both **Add to cart** and **Buy it now**. Buy it now clears the current bag and starts checkout with only that product.
- Seed catalog media is local SVG artwork in `static/uploads/`, so the demo catalog does not depend on external image URLs.


## HomeNest brand + product gallery update

The supplied HomeNest logo is bundled locally as `static/uploads/homenest-logo.png` and used by default for the storefront header/footer, favicon, admin navigation and store settings preview. Older `homenest-logo.svg` default references are upgraded automatically when the app loads settings.

The product gallery now uses a thumbnail-led gallery, desktop hover inspection, full-screen lightbox, previous/next controls, zoom controls, wheel zoom, drag-to-pan, double-click zoom, touch swipe and pinch-to-zoom.


Branding note: the supplied full HomeNest logo image is bundled locally and used as the canonical storefront/admin logo; it is preserved with contain sizing so the complete logo is visible.


## COD + prepaid delivery fee
The checkout supports a Pakistan-friendly split-payment flow: the customer can pay the delivery fee online and pay the remaining product balance to the courier on delivery. Partial COD/deposit patterns are supported by established ecommerce tooling, and Pakistani stores also publish this exact delivery-fee-prepaid/COD structure.

For real online payments, configure Safepay in `.env`:
- `SAFEPAY_ENV=sandbox` while testing
- `SAFEPAY_API_KEY=...`
- `SAFEPAY_V1_SECRET=...`
- `SAFEPAY_WEBHOOK_SECRET=...`
- `PUBLIC_BASE_URL=https://your-public-domain` in production

The production webhook endpoint is `/webhooks/safepay`. The app treats signed gateway confirmations as the payment source and does not mark the delivery fee paid merely because a customer lands on a success URL.
