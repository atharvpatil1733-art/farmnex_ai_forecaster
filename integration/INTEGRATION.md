# How to connect the forecaster to FarmNex (Flutter + FastAPI + Supabase)

This guide is written for beginners. Do the steps in order. Each step ends with a
**Check** so you know it worked before moving on.

## The big picture

```
 Farmer's phone                Your FarmNex backend              Forecaster (this repo)
 (Flutter app)   ──────────►   (FastAPI)            ──────────►  (FastAPI, new service)
                  login token      │  secret key (X-API-Key)
                                   ▼
                              Supabase (PostgreSQL)
                              - checks the farmer's login
                              - saves every forecast in table forecast_logs
```

- The **app only talks to your backend**, never directly to the forecaster.
- The **backend** checks the farmer is logged in, asks the forecaster, saves the answer in
  Supabase, and sends it back to the app.
- The **forecaster** runs on its own. Only your backend knows its secret key.

The files you will copy are in this `integration/` folder:

| File | Goes into |
|---|---|
| `backend/farmnex_forecast.py` | your FastAPI backend project |
| `supabase/001_forecast_logs.sql` | Supabase SQL Editor (run once) |
| `flutter/lib/services/forecast_api.dart` | your Flutter app, `lib/services/` |
| `flutter/lib/widgets/ceda_credit.dart` | your Flutter app, `lib/widgets/` |
| `flutter/lib/screens/price_forecast_screen.dart` | your Flutter app, `lib/screens/` (example screen) |

---

## Step 1: Put the forecaster online (Render.com, no Docker needed)

You need a website address where the forecaster runs 24/7. Render.com is the simplest: you
point it at this GitHub repo and type two commands.

1. **Make a secret key.** This is a long random password that only your backend will know.
   Use any password generator and make it at least 30 characters, or run
   `python -c "import secrets; print(secrets.token_urlsafe(32))"`.
   Save it somewhere safe; you need it again in Step 3.
2. Go to <https://render.com> and **sign up with your GitHub account**.
3. Click **New +** → **Web Service** → pick the repo **farmnex_ai_forecaster**. If it isn't
   listed, click "Configure account" and allow Render to see the repo.
4. Fill in the form:

   | Field | Value |
   |---|---|
   | Name | `farmnex-forecaster` (anything) |
   | Branch | `main` |
   | Language / Runtime | **Python 3** |
   | Build Command | `pip install -r requirements.txt` |
   | Start Command | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
   | Instance type | **Free** is fine for testing. **Starter** (about $7/month) never sleeps; use it when real farmers use the app. |

5. Open **Environment** (or "Advanced" → "Add Environment Variable") and add:

   | Key | Value |
   |---|---|
   | `PYTHON_VERSION` | `3.11.9` |
   | `FARMNEX_FORECASTER_API_KEY` | the secret key from step 1 |

6. Click **Create Web Service**. The first build takes about 5–10 minutes.

**Check:** open `https://farmnex-forecaster.onrender.com/health`, using the address Render shows
at the top of the page. You should see something like:

```json
{"status":"ok","model_version":"...","data_as_of":"2026-09-28"}
```

Then open `https://farmnex-forecaster.onrender.com/meta`. It should say
`missing or wrong X-API-Key`. That's correct: it means the forecaster is protected.

> The Free plan "sleeps" after 15 minutes without use, and the next request then takes about a
> minute. The code below waits long enough, but farmers will notice the delay. The Starter plan
> fixes it.

---

## Step 2: Create the table in Supabase

1. Open your project on <https://supabase.com/dashboard>.
2. In the left menu, click **SQL Editor** → **New query**.
3. Open `integration/supabase/001_forecast_logs.sql`, copy **everything**, paste it in, and
   click **Run**.
4. Find your keys: **Project Settings** → **API** (or **API Keys**). Write down three things:
   - **Project URL**, e.g. `https://abcd1234.supabase.co`
   - the **anon public** key (also called **publishable**)
   - the **service_role** key (also called **secret**). **Never put this key in the Flutter
     app.** It belongs only in the backend.

**Check:** **Table Editor** now shows a table called `forecast_logs`, with no rows yet.

---

## Step 3: Add the forecast routes to your FastAPI backend

1. Copy `integration/backend/farmnex_forecast.py` into your backend project, in the same folder
   as your `main.py`.
2. Make sure `httpx` is installed: add `httpx` to your backend's `requirements.txt` and run
   `pip install httpx`.
3. In your backend's `main.py`, add these two lines (after `app = FastAPI(...)`):

   ```python
   from farmnex_forecast import router as forecast_router
   app.include_router(forecast_router)
   ```

4. Add these settings to your backend's environment: its `.env` file, or the "Environment"
   page wherever the backend is hosted.

   ```
   FORECASTER_URL=https://farmnex-forecaster.onrender.com
   FORECASTER_API_KEY=<the same secret key as in Step 1>
   SUPABASE_URL=https://abcd1234.supabase.co
   SUPABASE_ANON_KEY=<anon public / publishable key>
   SUPABASE_SERVICE_ROLE_KEY=<service_role / secret key>
   ```

   If your backend doesn't load `.env` files automatically, add these two lines at the very top
   of `main.py`:

   ```python
   from dotenv import load_dotenv
   load_dotenv()
   ```

   You'll also need `pip install python-dotenv`.

5. Restart your backend.

**Check:** open your backend's docs page (e.g. `http://localhost:8000/docs`). You should see a
new **forecast** section:

| Route | Login needed? | What it does |
|---|---|---|
| `GET /forecast/meta` | no | lists for dropdowns and the CEDA credit |
| `GET /forecast/health` | no | is the forecaster up, and how new is its data |
| `GET /forecast/price?market=Pune&crop=Onion` | yes | prices for the next 3 days |
| `GET /forecast/demand?district=Pune` | yes | HIGH / NORMAL / LOW per crop |
| `POST /forecast/sell-options` | yes | best market and day to sell |
| `GET /forecast/crops?district=Pune&sowing_month=6` | yes | which crop to sow |

Try `GET /forecast/meta` in the docs page. It should return markets and crops. The other routes
return `401 log in first` from the docs page, which is correct: the app sends the login.

> Already have your own login check in the backend? Replace `Depends(current_user_id)` in
> `farmnex_forecast.py` with your own dependency; it only needs to return the user's id.

---

## Step 4: Use it in the Flutter app

1. In `pubspec.yaml`, under `dependencies:`, add (you already have `supabase_flutter`):

   ```yaml
   http: ^1.2.0
   ```

   Then run `flutter pub get`.
2. Copy the three Dart files from `integration/flutter/lib/` into the same folders in your app
   (`lib/services/`, `lib/widgets/`, `lib/screens/`).
3. **CEDA logo:** this is required by the data licence.
   - Download the official logo from <https://ceda.ashoka.edu.in/api-terms-conditions/>.
   - Save it as `assets/images/ceda_logo.png`.
   - Add it to `pubspec.yaml`:

   ```yaml
   flutter:
     assets:
       - assets/images/ceda_logo.png
   ```

4. Create the API object once, with your **backend's** address (not the forecaster's):

   ```dart
   import 'services/forecast_api.dart';

   final forecastApi = ForecastApi(backendUrl: 'https://api.your-farmnex-backend.com');
   ```

   To test against a backend running on your own computer from the Android emulator, use
   `http://10.0.2.2:8000`.
5. Open the example screen from any button:

   ```dart
   import 'screens/price_forecast_screen.dart';

   Navigator.push(context, MaterialPageRoute(
     builder: (_) => PriceForecastScreen(api: forecastApi),
   ));
   ```

6. **Android only:** make sure `android/app/src/main/AndroidManifest.xml` has this line above
   `<application`. Release builds need it to use the internet.

   ```xml
   <uses-permission android:name="android.permission.INTERNET"/>
   ```

**Check:** log in to the app, open the screen, and pick **Pune** and **Onion**. You should see 3
days of prices ("about Rs 2,963 / quintal ..."), the reasons, and the CEDA credit at the bottom
right. Then, in Supabase **Table Editor** → `forecast_logs`, a new row should appear with your
user id.

### Other screens (same pattern as the example)

```dart
final demand = await forecastApi.getDemand('Pune');                 // demand['items'][i]['signal']
final sell = await forecastApi.getSellOptions(
    lat: 18.52, lon: 73.85, crop: 'Onion', qtyQuintal: 20);          // sell['best']['market'], ['best_day'], ['asking_price']
final crops = await forecastApi.getCropSuggestions('Pune', 6);      // crops['items'][i]['crop'], ['expected_price']
```

- Get the farmer's `lat` / `lon` from your existing location code (e.g. the `geolocator` package).
- Every answer has a `reason` list (show it as bullet points) and an `as_of` date (show
  "based on mandi data up to ...").
- On every screen that shows these prices, put `CedaCredit(text: meta['attribution'])` at the
  bottom right.

---

## Step 5: Final test checklist

- [ ] `https://<forecaster>/health` shows `"status":"ok"`.
- [ ] `https://<forecaster>/meta` without the key says `missing or wrong X-API-Key`.
- [ ] Backend `/forecast/meta` returns markets.
- [ ] In the app, logged in: price, demand, sell-options and crop screens show data.
- [ ] Supabase `forecast_logs` gets a new row for each forecast.
- [ ] The CEDA logo and credit are visible at the bottom right of price screens.

## If something goes wrong

| What you see | What it means | Fix |
|---|---|---|
| App: "price forecasts are temporarily unavailable" | The backend can't reach the forecaster, or its key is wrong | Check `FORECASTER_URL` and that `FORECASTER_API_KEY` matches `FARMNEX_FORECASTER_API_KEY` on Render exactly |
| App: "log in first" / "your login has expired" | No or old Supabase login token | Log in again; check `SUPABASE_URL` and `SUPABASE_ANON_KEY` in the backend |
| App waits about a minute, then works | Render Free plan was asleep | Normal on Free; switch to Starter |
| App: "unknown market ..." / "unknown crop ..." | A name not in `/forecast/meta` | Fill dropdowns only from `getMeta()` |
| App: "no real ... prices ...; synthetic data is hidden" | That market has no real data for that crop | Only offer crops listed in `meta['markets'][i]['crops']` (the example screen does this) |
| Nothing saved in `forecast_logs` | Service key missing or table not created | Check `SUPABASE_SERVICE_ROLE_KEY`; rerun the SQL file. Backend logs say "could not save forecast log" with the reason |
| Render build fails | Wrong Python version | Set `PYTHON_VERSION` = `3.11.9` and redeploy |
| Render logs: `libgomp.so.1: cannot open shared object file` | The server is missing a system library the prediction model (LightGBM) needs | Copy the full error and ask Claude Code to fix it; the usual fix is a small change to the Render build settings |

## Keeping prices fresh

The forecaster answers from its newest mandi data (now 28 Sep 2026). It does **not** download new
prices by itself yet. To update:

1. Download new "Daily Price Arrival Report" CSVs from agmarknet.gov.in (same kind of files as in
   `data/raw/`) and upload them to `data/raw/` on GitHub.
2. Rebuild the data and retrain. Either ask Claude Code to "refresh the data and retrain", or on
   a computer with Python 3.11 run:
   `pip install -r requirements.txt && python -m forecaster.data && python -m forecaster.train`,
   then commit and push.
3. Render sees the new commit on `main` and redeploys by itself (a few minutes).

## Licence reminder

The prices come from CEDA (Ashoka University) / Agmarknet: **free for non-commercial use only**.
Show their logo and credit, and don't imply they endorse FarmNex. If FarmNex earns money, ask
CEDA for permission first (<https://ceda.ashoka.edu.in/api-terms-conditions/>).
