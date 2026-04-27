# MVP Demo Script

Live web demo: https://project2-three-rho.vercel.app  
API docs: https://macau-shopping-api.onrender.com/docs

## Goal

Show that the deployed MVP can turn a local shopping intent into practical Macau shopping guidance using the available price dataset and collection-point context.

## Audience

- Product reviewers
- Demo stakeholders
- Technical evaluators who want to inspect the API contract

## Pre-demo checklist

1. Open the web demo URL in a fresh browser tab.
2. Open the API docs URL in a second tab.
3. Confirm the web app loads without a browser error.
4. Confirm the API docs page loads and exposes FastAPI/OpenAPI endpoints.
5. Keep this script and `docs/screenshots/README.md` available for capture notes.

## 5-minute walkthrough

### 1. Introduce the problem

"This MVP helps a shopper in Macau compare nearby basket options from processed public price data. The current scope is demo guidance, not final checkout or route optimization."

### 2. Show the live web demo

- Navigate to https://project2-three-rho.vercel.app
- Point out the main input area and any default/demo collection point.
- Enter or reuse a representative basket, for example:

```text
?????????????????
```

### 3. Explain the output

Highlight:

- Parsed basket items
- Nearby collection-point context
- Recommended shopping option
- Price or signal differences where available
- Any visible confidence, fallback, or missing-data messaging

### 4. Show API docs

- Navigate to https://macau-shopping-api.onrender.com/docs
- Point out that the backend exposes a documented API contract.
- Use the docs page to show request/response structure for the main demo endpoint.

### 5. Close with MVP boundaries

State clearly:

- Prices are for reference and should be checked against store labels.
- The MVP uses the currently available processed data.
- It is not yet a full production shopping, inventory, or routing system.

## Suggested demo success criteria

- Web demo loads from the public URL.
- API docs load from the public URL.
- A sample basket produces a user-readable recommendation.
- Demo limitations are communicated transparently.

## Backup path

If the public web demo is temporarily unavailable, use the API docs URL to demonstrate the deployed backend contract and reference `DEMO_README.md` for local command-line demo steps.
