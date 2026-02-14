// 部署到 Cloudflare Worker
export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const key = "NET_LIMIT_STATUS";
    if (request.method === "POST" && url.pathname === "/api/set") {
      const body = await request.json();
      await env.APP_CONFIG.put(key, body.status ? "1" : "0");
      return new Response(JSON.stringify({ success: true, status: body.status }));
    }
    if (request.method === "GET" && url.pathname === "/api/check") {
      const val = await env.APP_CONFIG.get(key);
      return new Response(JSON.stringify({ limited: val === "1" }));
    }
    const currentStatus = await env.APP_CONFIG.get(key) === "1";
    const html = `<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1"><style>body{font-family:sans-serif;text-align:center;padding:50px}.btn{padding:20px 40px;font-size:24px;border:none;border-radius:10px;cursor:pointer;color:white}.red{background-color:#e74c3c}.green{background-color:#2ecc71}</style></head><body><h1>Net Control</h1><h2>${currentStatus?"🔴 LIMITED":"🟢 NORMAL"}</h2><button class="btn red" onclick="s(true)">Limit</button> <button class="btn green" onclick="s(false)">Unlock</button><script>async function s(l){await fetch('/api/set',{method:'POST',body:JSON.stringify({status:l})});location.reload()}</script></body></html>`;
    return new Response(html, { headers: { 'Content-Type': 'text/html;charset=UTF-8' } });
  }
};