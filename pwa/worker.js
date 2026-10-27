const STREAMLIT_URL = "https://hack-for-humanity-dhtqzvofebzbjrsyunlnmz.streamlit.app";

const SERVICE_WORKER = `const CACHE="dhoa-v1";
self.addEventListener("install",()=>self.skipWaiting());
self.addEventListener("activate",()=>self.clients.claim());
self.addEventListener("fetch",(e)=>{
  e.respondWith(fetch(e.request).catch(()=>caches.match(e.request)));
});`;

const ICON_192 = Uint8Array.from(atob("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"), (char) => char.charCodeAt(0));
const ICON_512 = Uint8Array.from(atob("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"), (char) => char.charCodeAt(0));

const iconResponse = (icon) =>
  new Response(icon, {
    headers: {
      "Content-Type": "image/png",
      "Cache-Control": "public, max-age=31536000, immutable",
    },
  });

const MANIFEST = JSON.stringify({
  name: "Dhoa – ইটভাটা পর্যবেক্ষণ",
  short_name: "Dhoa",
  start_url: "/",
  display: "standalone",
  background_color: "#0f1419",
  theme_color: "#0072b2",
  icons: [
    { src: "/icon-192.png", sizes: "192x192", type: "image/png", purpose: "any maskable" },
    { src: "/icon-512.png", sizes: "512x512", type: "image/png", purpose: "any maskable" },
  ],
});

const SHELL = `<!doctype html>
<html lang="bn">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <meta name="theme-color" content="#0072b2">
  <meta name="apple-mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-title" content="Dhoa">
  <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
  <link rel="manifest" href="/manifest.json">
  <link rel="apple-touch-icon" href="/icon.png">
  <title>Dhoa</title>
  <style>
    html, body { width: 100%; height: 100%; margin: 0; background: #0f1419; }
    iframe { position: fixed; inset: 0; width: 100%; height: 100%; border: 0; }
    #install-card {
      position: fixed; z-index: 10000; top: max(12px, env(safe-area-inset-top));
      left: 50%; transform: translateX(-50%); width: min(92vw, 420px);
      box-sizing: border-box; padding: 10px 12px; border-radius: 14px;
      color: #fff; background: #17232d; box-shadow: 0 4px 20px #0008;
      font: 14px system-ui, sans-serif;
    }
    #install-card[hidden], #install-help[hidden] { display: none; }
    #install-action {
      border: 0; border-radius: 9px; padding: 10px 14px; color: #fff;
      background: #0072b2; font: inherit; font-weight: 700;
    }
    #install-close { float: right; border: 0; color: #fff; background: transparent; font: 20px system-ui; }
    #install-help { margin: 8px 0 0; line-height: 1.45; }
    @media (pointer: fine), (min-width: 769px) {
      #install-card { display: none !important; }
    }
  </style>
</head>
<body>
  <iframe src="${STREAMLIT_URL}/?lang=bn&amp;embed=true" allow="geolocation; camera; microphone" allowfullscreen></iframe>
  <aside id="install-card" hidden aria-label="Install Dhoa">
    <button id="install-action" type="button">Install Dhoa · ধোঁয়া ইনস্টল করুন</button>
    <button id="install-close" type="button" aria-label="Dismiss">×</button>
    <p id="install-help" hidden>Android Chrome: tap ⋮, then Install. iPhone: open this link in Safari and choose Share → Add to Home Screen.<br>অ্যান্ড্রয়েড: ⋮ চাপুন, তারপর Install। iPhone: Safari-তে খুলে Share → Add to Home Screen চাপুন।</p>
  </aside>
  <script>
    if ("serviceWorker" in navigator) navigator.serviceWorker.register("/sw.js");
    const installCard = document.getElementById("install-card");
    const installHelp = document.getElementById("install-help");
    let installPrompt = null;
    const mobileInstallUi = matchMedia("(max-width: 768px) and (pointer: coarse)").matches;
    const isInstalled = matchMedia("(display-mode: standalone)").matches || navigator.standalone;
    if (mobileInstallUi && !isInstalled && !localStorage.getItem("dhoa-install-dismissed")) installCard.hidden = false;
    window.addEventListener("beforeinstallprompt", (event) => {
      if (!mobileInstallUi || isInstalled || localStorage.getItem("dhoa-install-dismissed")) return;
      event.preventDefault();
      installPrompt = event;
      installCard.hidden = false;
    });
    document.getElementById("install-action").addEventListener("click", async () => {
      if (!installPrompt) {
        installHelp.hidden = !installHelp.hidden;
        return;
      }
      const prompt = installPrompt;
      installPrompt = null;
      await prompt.prompt();
      if ((await prompt.userChoice).outcome === "accepted") installCard.hidden = true;
    });
    document.getElementById("install-close").addEventListener("click", () => {
      installCard.hidden = true;
      localStorage.setItem("dhoa-install-dismissed", "1");
    });
    window.addEventListener("appinstalled", () => { installCard.hidden = true; });
  </script>
</body>
</html>`;

export default {
  async fetch(request) {
    const { pathname } = new URL(request.url);

    if (pathname === "/sw.js") {
      return new Response(SERVICE_WORKER, {
        headers: {
          "Content-Type": "application/javascript; charset=utf-8",
          "Service-Worker-Allowed": "/",
        },
      });
    }

    if (pathname === "/manifest.json") {
      return new Response(MANIFEST, {
        headers: { "Content-Type": "application/manifest+json; charset=utf-8" },
      });
    }

    if (pathname === "/icon-192.png") return iconResponse(ICON_192);
    if (pathname === "/icon-512.png" || pathname === "/icon.png") {
      return iconResponse(ICON_512);
    }

    return new Response(SHELL, {
      headers: { "Content-Type": "text/html; charset=utf-8" },
    });
  },
};

\n