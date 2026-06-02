import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

let cachedToken = null;
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const rootDir = path.resolve(__dirname, "..", "..");

function base64Url(input) {
  return Buffer.from(input).toString("base64url");
}

function loadCredentials() {
  const envJson = process.env.AUTOMATION_GOOGLE_CREDENTIALS_JSON?.trim();
  if (envJson) {
    return JSON.parse(envJson);
  }

  const candidates = [
    process.env.AUTOMATION_GOOGLE_CREDENTIALS,
    process.env.GOOGLE_APPLICATION_CREDENTIALS,
    path.join(rootDir, "credentials.json"),
    path.join(rootDir, "backup", "js-migration-20260527", "enquiry", "credentials.json"),
  ].filter(Boolean);

  const credentialPath = candidates.find((candidate) => fs.existsSync(candidate));
  if (!credentialPath) {
    throw new Error("Google credentials not found for sheet logging.");
  }

  return JSON.parse(fs.readFileSync(credentialPath, "utf8"));
}

async function accessToken() {
  if (cachedToken && cachedToken.expiresAt > Date.now() + 60_000) {
    return cachedToken.value;
  }

  const credentials = loadCredentials();
  const tokenUri = credentials.token_uri || "https://oauth2.googleapis.com/token";
  const nowSeconds = Math.floor(Date.now() / 1000);
  const unsignedJwt = [
    base64Url(JSON.stringify({ alg: "RS256", typ: "JWT" })),
    base64Url(
      JSON.stringify({
        iss: credentials.client_email,
        scope: "https://www.googleapis.com/auth/drive.readonly https://www.googleapis.com/auth/spreadsheets",
        aud: tokenUri,
        iat: nowSeconds,
        exp: nowSeconds + 3600,
      }),
    ),
  ].join(".");
  const signature = crypto.createSign("RSA-SHA256").update(unsignedJwt).sign(credentials.private_key);
  const assertion = `${unsignedJwt}.${base64Url(signature)}`;

  const response = await fetch(tokenUri, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      grant_type: "urn:ietf:params:oauth:grant-type:jwt-bearer",
      assertion,
    }),
  });
  const payload = await response.json();
  if (!response.ok || !payload.access_token) {
    throw new Error(payload.error_description || "Google authentication failed.");
  }

  cachedToken = {
    value: payload.access_token,
    expiresAt: Date.now() + Number(payload.expires_in || 3600) * 1000,
  };
  return cachedToken.value;
}

async function googleJson(url, init) {
  const token = await accessToken();
  const response = await fetch(url, {
    ...init,
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
      ...(init?.headers || {}),
    },
  });
  const payload = await response.json();
  if (!response.ok) {
    const error = payload;
    throw new Error(error.error?.message || `Google API request failed with ${response.status}`);
  }
  return payload;
}

export async function spreadsheetIdForTitle(sheetName) {
  const escapedName = sheetName.replaceAll("\\", "\\\\").replaceAll("'", "\\'");
  const query = encodeURIComponent(
    `name='${escapedName}' and mimeType='application/vnd.google-apps.spreadsheet' and trashed=false`,
  );
  const payload = await googleJson(
    `https://www.googleapis.com/drive/v3/files?q=${query}&fields=files(id)&supportsAllDrives=true&includeItemsFromAllDrives=true`,
  );
  const spreadsheetId = payload.files?.[0]?.id;
  if (!spreadsheetId) {
    throw new Error(`Google Sheet not found: ${sheetName}`);
  }
  return spreadsheetId;
}

export async function appendSheetRows(sheetName, tabName, rows) {
  if (!rows.length) {
    return;
  }
  const spreadsheetId = await spreadsheetIdForTitle(sheetName);
  const range = encodeURIComponent(`'${tabName.replaceAll("'", "''")}'!A:H`);
  await googleJson(
    `https://sheets.googleapis.com/v4/spreadsheets/${spreadsheetId}/values/${range}:append?valueInputOption=USER_ENTERED&insertDataOption=INSERT_ROWS`,
    {
      method: "POST",
      body: JSON.stringify({ values: rows }),
    },
  );
}
