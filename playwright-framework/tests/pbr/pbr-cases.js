const buyerHome = process.env.PBR_BUYER_HOME_URL || "https://buyer.indiamart.com/";
const searchCity =
  process.env.PBR_SEARCH_CITY_URL || "https://dir.indiamart.com/search.mp?ss=shoes&search_type=p&src=adv-srch";
const searchAllIndia =
  process.env.PBR_SEARCH_ALL_INDIA_URL ||
  "https://dir.indiamart.com/search.mp?ss=chairs&search_type=p&mcatid=3712&catid=93&v=4&crs=cs-all";
const mcat = process.env.PBR_MCAT_URL || "https://dir.indiamart.com/impcat/office-chairs.html";
const dirHome = process.env.PBR_DIR_HOME_URL || "https://dir.indiamart.com/";
const dirHeader = process.env.PBR_DIR_HEADER_URL || "https://dir.indiamart.com/";
const pdp =
  process.env.PBR_PDP_URL ||
  "https://www.indiamart.com/proddetail/oppo-mobile-phones-2851972054933.html";
const company = process.env.PBR_COMPANY_URL || "https://www.indiamart.com/raghavendraagency-hyderabad/";

const submitRequirement = "button#t0102_submit, input#t0102_submit, input#t0101_submit, button:has-text('Submit Requirement')";
const chatBl = "button:has-text('Chat Now'), button:has-text('Get Best Price'), button:has-text('Contact Supplier')";

function pbrCase(title, url, openSelector = submitRequirement, ctaClicks = 4) {
  return { title, url, openSelector, ctaClicks, productName: "office chair" };
}

export const pbrCases = [
  pbrCase("Fully logged in buyer submits PBR form on company page", company, "input#t0101_submit, button:has-text('Submit Requirement')", 5),
  pbrCase("Fully logged in buyer submits PBR form on DIR header", dirHeader, submitRequirement, 4),
  pbrCase("Fully logged in buyer submits PBR form on DIR home page", dirHome, submitRequirement, 4),
  pbrCase("Fully logged in buyer submits PBR form on MCAT page", mcat, submitRequirement, 5),
  pbrCase("Fully logged in buyer submits PBR form on BuyerMy home page", buyerHome, "button:has-text('Get Quotes'), button:has-text('Submit Requirement')", 4),
  pbrCase("Fully logged in buyer submits PBR form on BuyerMy my orders page", `${buyerHome}orders`, "input#t0901_submit, button:has-text('Submit Requirement')", 4),
  pbrCase("Fully logged in buyer submits PBR form on BuyerMy recommended categories", buyerHome, "button.submit-button, button:has-text('Get Quotes')", 4),
  pbrCase("Fully logged in buyer submits PBR form on PDP page", pdp, submitRequirement, 5),
  pbrCase("Fully logged in buyer submits BL via chatBL form on PDP page", pdp, chatBl, 5),
  pbrCase("Fully logged in buyer submits PBR form on search all India page", searchAllIndia, "button#t0102_submit, button:has-text('Submit Requirement')", 4),
  pbrCase("Fully logged in buyer submits PBR form on search city page", searchCity, "button#t0102_submit, button:has-text('Submit Requirement')", 4),
  pbrCase("Fully logged in buyer submits BL via chatBL form on search page", searchCity, chatBl, 4),
  pbrCase("Identified buyer submits PBR form on company page", company, "input#t0101_submit, button:has-text('Submit Requirement')", 5),
  pbrCase("Identified buyer submits PBR form on DIR header", dirHeader, submitRequirement, 4),
  pbrCase("Identified buyer submits PBR form on DIR home page", dirHome, submitRequirement, 4),
  pbrCase("Identified buyer submits PBR form on MCAT page", mcat, submitRequirement, 5),
  pbrCase("Identified buyer submits PBR form on PDP page", pdp, submitRequirement, 5),
  pbrCase("Identified buyer submits BL via chatBL form on PDP page", pdp, chatBl, 5),
  pbrCase("Identified buyer submits PBR form on search all India page", searchAllIndia, "button#t0102_submit, button:has-text('Submit Requirement')", 4),
  pbrCase("Identified buyer submits PBR form on search city page", searchCity, "button#t0102_submit, button:has-text('Submit Requirement')", 4),
  pbrCase("Identified buyer submits BL via chatBL form on search page", searchCity, chatBl, 4),
];
