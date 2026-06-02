import { expect } from "@playwright/test";

export const bmcUrls = {
  buyerHome: process.env.BMC_BUYER_HOME_URL || "https://buyer.indiamart.com/",
  messageCentre: process.env.BMC_MESSAGE_CENTRE_URL || "https://buyer.indiamart.com/enquiry/messagecentre/",
  myOrders: process.env.BMC_MY_ORDERS_URL || "https://buyer.indiamart.com/orders",
};

export const bmcSelectors = {
  contactCard: "div.message-user-name-section, .message-user-name-section, .left_det_show, div[class*='message-user-name']",
  contactName: "div.message-user-name-section .c_name, div.wrd_elip.c_name, .c_name",
  conversation: ".header-font, div[class*='conversation'], div[class*='message']",
  search: "input#searchauto, input[placeholder*='Search'], input[placeholder*='search']",
  messageBox: "textarea, [contenteditable='true'], input[placeholder*='message'], input[placeholder*='Message']",
  sendButton: "#send_button, button:has-text('Send'), [type='submit']",
  attachmentInput: "input[type='file']",
};

export async function openMessageCentre(page) {
  await page.goto(bmcUrls.messageCentre, { waitUntil: "domcontentloaded" });
  await expect(page.locator(bmcSelectors.contactCard).first(), "Message centre contact list should be visible").toBeVisible({
    timeout: 20_000,
  });
}

export async function openFirstConversation(page) {
  await openMessageCentre(page);
  const firstContact = page.locator(bmcSelectors.contactName).first();
  await expect(firstContact, "First contact should be visible").toBeVisible();
  await firstContact.click();
  await expect(page.locator(bmcSelectors.conversation).first(), "Conversation should open").toBeVisible({ timeout: 15_000 });
}

export async function sendMessage(page, message) {
  const box = page.locator(bmcSelectors.messageBox).first();
  await expect(box, "Message input should be visible").toBeVisible({ timeout: 15_000 });
  await box.fill(message).catch(async () => {
    await box.click();
    await page.keyboard.type(message);
  });
  await page.locator(bmcSelectors.sendButton).first().click();
  await expect(page.locator(`text=${message}`).first(), "Sent message should appear in conversation").toBeVisible({
    timeout: 15_000,
  });
}
