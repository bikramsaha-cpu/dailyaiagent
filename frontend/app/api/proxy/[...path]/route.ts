import { NextRequest, NextResponse } from "next/server";

const API_SERVER_URL = process.env.API_SERVER_URL?.replace(/\/$/, "") || "http://127.0.0.1:8000";

async function proxy(request: NextRequest, params: { path?: string[] }, method: string) {
  const path = (params.path || []).join("/");
  const target = new URL(`${API_SERVER_URL}/api/${path}`);
  request.nextUrl.searchParams.forEach((value, key) => {
    target.searchParams.append(key, value);
  });

  const init: RequestInit = {
    method,
    headers: {
      "Content-Type": request.headers.get("content-type") || "application/json",
    },
    cache: "no-store",
  };

  if (!["GET", "HEAD"].includes(method)) {
    init.body = await request.text();
  }

  try {
    const response = await fetch(target, init);
    const text = await response.text();
    return new NextResponse(text, {
      status: response.status,
      headers: {
        "Content-Type": response.headers.get("content-type") || "application/json",
      },
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown proxy error";
    return NextResponse.json(
      {
        detail: `Could not reach backend at ${API_SERVER_URL}. ${message}`,
      },
      { status: 502 },
    );
  }
}

export async function GET(
  request: NextRequest,
  context: { params: Promise<{ path?: string[] }> },
) {
  const params = await context.params;
  return proxy(request, params, "GET");
}

export async function POST(
  request: NextRequest,
  context: { params: Promise<{ path?: string[] }> },
) {
  const params = await context.params;
  return proxy(request, params, "POST");
}
