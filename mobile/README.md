# KilnWatch Mobile

Expo demo for nearby kiln candidates, a field map, and field capture.

## Run

```powershell
cd mobile
npm install
npm start
```

Set `EXPO_PUBLIC_API_URL` in `.env` when the backend is reachable. The app
uses one real candidate fallback when the API is offline.

The backend can run locally from the repository root:

```powershell
python -m uvicorn backend.main:app --reload
```

## Demo

- **Home:** candidate cards.
- **Map:** markers and nearby lookup.
- **Capture:** note and camera flow.

Backend deployment steps for Render or Railway are documented in the root
README.
