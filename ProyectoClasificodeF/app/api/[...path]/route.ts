export const runtime = "nodejs";

const BACKEND_BASE = process.env.BACKEND_BASE_URL || "http://127.0.0.1:5000";

// Next.js 15: params must be awaited
async function proxy(req: Request, ctx: { params: Promise<{ path?: string[] }> }) {
  const url = new URL(req.url);
  const { path = [] } = await ctx.params;

  // Optional: map simple aliases to backend auth endpoints
  const segs = [...path];
  if (segs.length > 0) {
    if (segs[0] === "login" || segs[0] === "register" || segs[0] === "logout" || segs[0] === "validate") {
      segs.unshift("auth");
    }
  }

  const target = `${BACKEND_BASE.replace(/\/$/, "")}/${segs.join("/")}${url.search}`;

  const headers = new Headers(req.headers);
  headers.delete("host");
  headers.delete("connection");
  headers.delete("content-length");
  headers.delete("accept-encoding");
  headers.set("x-forwarded-by", "next-proxy");

  let body: BodyInit | undefined = undefined;
  const method = req.method.toUpperCase();
  const ct = req.headers.get("content-type") || "";

  if (method !== "GET" && method !== "HEAD") {
    if (ct.includes("application/json")) {
      const json = await req.json();
      body = JSON.stringify(json);
      headers.set("content-type", "application/json");
    } else if (ct.includes("multipart/form-data")) {
      const form = await req.formData();
      const f = new FormData();
      form.forEach((v, k) => f.append(k, v as any));
      body = f;
      headers.delete("content-type");
    } else if (ct.includes("application/x-www-form-urlencoded")) {
      const text = await req.text();
      body = text;
      headers.set("content-type", "application/x-www-form-urlencoded");
    } else {
      const buf = await req.arrayBuffer();
      body = buf;
    }
  }

  const res = await fetch(target, { method, headers, body });
  const resHeaders = new Headers(res.headers);
  return new Response(res.body, { status: res.status, headers: resHeaders });
}

export { proxy as GET, proxy as POST, proxy as PUT, proxy as PATCH, proxy as DELETE };
