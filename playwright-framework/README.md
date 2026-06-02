# Enquiry Playwright Framework

Clean TypeScript Playwright framework for the Daily QA Agent enquiry module.

## Structure

```text
playwright-framework/
  package.json
  playwright.config.ts
  tests/
    enquiry/
      setup/
      smoke/
    pbr/
      setup/
      smoke/
    bmc/
      setup/
      smoke/
  data/
  utils/
  test-results/
```

Each module has its own `setup/buyer-login.setup.ts` and saved session:

- Enquiry: `test-results/auth/enquiry-buyer.json`
- PBR: `test-results/auth/pbr-buyer.json`
- BMC: `test-results/auth/bmc-buyer.json`

The module tests run after their matching setup and reuse the saved session.

## Commands

```bash
npm install
npx playwright install
npm run test:enquiry
npm run test:enquiry:headed
```

Environment values can be set in the shell:

```bash
ENQUIRY_BASE_URL=https://dir.indiamart.com
ENQUIRY_SEARCH_TERM=hat
ENQUIRY_ALL_INDIA_SEARCH_TERM=headphones
ENQUIRY_IMPCAT_URL=https://dir.indiamart.com/impcat/denim-clothing.html
ENQUIRY_PDP_URL=https://www.indiamart.com/proddetail/oppo-mobile-phones-2851972054933.html
ENQUIRY_COMPANY_URL=https://www.indiamart.com/raghavendraagency-hyderabad/
ENQUIRY_LOGIN_PHONE=9643193481
ENQUIRY_LOGIN_OTP=1956
ENQUIRY_SHEET_NAME=Buyer Automation
ENQUIRY_SHEET_TAB=ENQ
ENQUIRY_LOG_TO_SHEET=true
HEADLESS=false
```
