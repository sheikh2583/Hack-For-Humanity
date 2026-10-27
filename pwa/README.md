# One-time setup
npm install -g wrangler
wrangler login

# Deploy (run from inside pwa/)
cd pwa
wrangler deploy

# Your URL: https://dhoa-pwa.<your-subdomain>.workers.dev
# Android: open URL in Chrome → three-dot menu → Install app
# iOS: open URL in Safari → Share → Add to Home Screen

# Redeploy after any change:
wrangler deploy
