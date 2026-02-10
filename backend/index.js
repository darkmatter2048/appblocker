export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const path = url.pathname;

    // Helper to add CORS headers
    const corsHeaders = {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "GET, HEAD, POST, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type",
    };

    if (request.method === "OPTIONS") {
      return new Response(null, { headers: corsHeaders });
    }

    // 1. GET /: Serve the Control Dashboard
    if (path === "/" && request.method === "GET") {
      const html = `
      <!DOCTYPE html>
      <html>
      <head>
        <title>Network Control Center</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
          body { font-family: -apple-system, system-ui, sans-serif; max-width: 600px; margin: 20px auto; padding: 20px; background: #f0f2f5; }
          .card { background: white; padding: 20px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
          h1 { color: #1a1a1a; margin-top: 0; }
          input { width: 100%; padding: 12px; margin: 10px 0; border: 1px solid #ddd; border-radius: 8px; box-sizing: border-box; }
          button { width: 100%; padding: 12px; border: none; border-radius: 8px; font-weight: bold; cursor: pointer; transition: 0.2s; margin-top: 5px; }
          .btn-block { background: #ff4757; color: white; }
          .btn-allow { background: #2ed573; color: white; }
          .status-box { margin-top: 20px; padding: 15px; background: #f8f9fa; border-radius: 8px; text-align: center; font-size: 1.2em; }
          .loading { color: #666; }
        </style>
      </head>
      <body>
        <div class="card">
          <h1>Network Controller</h1>
          <p>Enter the Device ID displayed on the Android app.</p>
          <input type="text" id="deviceId" placeholder="e.g. device-123" />
          
          <div id="controls" style="display:none">
            <div class="status-box" id="currentStatus">Checking...</div>
            <br/>
            <button class="btn-block" onclick="setStatus(true)">🛑 BLOCK INTERNET (LAG)</button>
            <button class="btn-allow" onclick="setStatus(false)">✅ RESTORE INTERNET</button>
          </div>
          
          <button id="checkBtn" onclick="checkStatus()" style="background:#333; color:white;">Check Device</button>
        </div>

        <script>
          const apiUrl = window.location.origin;

          async function checkStatus() {
            const id = document.getElementById('deviceId').value;
            if(!id) return alert('Enter Device ID');
            
            document.getElementById('checkBtn').style.display = 'none';
            document.getElementById('controls').style.display = 'block';
            await refreshStatus();
          }

          async function refreshStatus() {
            const id = document.getElementById('deviceId').value;
            try {
              const res = await fetch(apiUrl + '/status?id=' + id);
              const data = await res.json();
              const statusDiv = document.getElementById('currentStatus');
              if(data.blocked) {
                statusDiv.innerHTML = 'Status: <b style="color:red">BLOCKED</b>';
              } else {
                statusDiv.innerHTML = 'Status: <b style="color:green">NORMAL</b>';
              }
            } catch(e) {
              alert('Error fetching status');
            }
          }

          async function setStatus(blocked) {
            const id = document.getElementById('deviceId').value;
            await fetch(apiUrl + '/update', {
              method: 'POST',
              headers: {'Content-Type': 'application/json'},
              body: JSON.stringify({ id, blocked })
            });
            await refreshStatus();
          }
        </script>
      </body>
      </html>
      `;
      return new Response(html, { headers: { "Content-Type": "text/html" } });
    }

    // 2. GET /status?id=...
    if (path === "/status" && request.method === "GET") {
      const id = url.searchParams.get("id");
      if (!id) return new Response("Missing ID", { status: 400 });

      // In a real app, use: await env.DEVICE_STATUS.get(id);
      // For this demo without binding setup, we try to use KV if bound, else default to false (safe fallback)
      let isBlocked = false;
      try {
        if(env.DEVICE_STATUS) {
           const val = await env.DEVICE_STATUS.get(id);
           isBlocked = val === "true";
        }
      } catch(e) {}

      return new Response(JSON.stringify({ id, blocked: isBlocked }), {
        headers: { ...corsHeaders, "Content-Type": "application/json" }
      });
    }

    // 3. POST /update
    if (path === "/update" && request.method === "POST") {
      try {
        const body = await request.json();
        const { id, blocked } = body;
        
        // Save to KV
        if(env.DEVICE_STATUS) {
            await env.DEVICE_STATUS.put(id, blocked ? "true" : "false");
        } else {
            return new Response(JSON.stringify({ error: "KV 'DEVICE_STATUS' not bound in wrangler.toml" }), { 
                status: 500, headers: corsHeaders 
            });
        }

        return new Response(JSON.stringify({ success: true, id, blocked }), {
          headers: { ...corsHeaders, "Content-Type": "application/json" }
        });
      } catch (e) {
        return new Response("Error", { status: 500, headers: corsHeaders });
      }
    }

    return new Response("Not Found", { status: 404 });
  }
};
