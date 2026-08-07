# Google Login API — Frontend Integration Reference

## Endpoint

```
POST /auth/google
Content-Type: application/json
```

No auth header required (this endpoint *is* how a token gets issued).

**Request**
```json
{ "id_token": "<Google ID token from Google Identity Services>" }
```

**Response `200`** — identical shape to the existing `POST /login`, so
whatever code already stores/uses the login response can be reused as-is:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "vstitch_user_id": 33,
  "vstitch_user_name": "anjali_nanda"
}
```
Use `access_token` exactly like the password-login token: `Authorization:
Bearer <access_token>` on every authenticated request afterward.

**Response `401`** (bad/expired/tampered token, or a Google account with no
verified email)
```json
{ "detail": "Invalid or expired Google credential." }
```

**Response `422`** (missing/empty `id_token` in the request body)
```json
{ "detail": [{ "type": "missing", "loc": ["body", "id_token"], "msg": "Field required" }] }
```

**Response `500`** (unexpected server error — generic, safe-to-display
message, never raw internal detail)
```json
{ "detail": "Something went wrong while signing in with Google. Please try again later." }
```

## What the frontend needs to send

`id_token` must be a **Google ID token**, not an access token and not an
authorization code. This comes from Google Identity Services (GIS) running
in the browser — the backend never talks to Google's OAuth consent screen
itself, it only verifies a token the frontend already obtained.

**Client ID to use in the frontend GIS config:**
```
698686810115-ruriejj8olt099g99qajcllmijkd5d7n.apps.googleusercontent.com
```
(Same `GOOGLE_CLIENT_ID` the backend verifies the token's audience against
— they must match exactly, or every login will 401.)

### Recommended integration (Google Identity Services "Sign in with Google" button)

```html
<script src="https://accounts.google.com/gsi/client" async defer></script>

<div id="g_id_onload"
     data-client_id="698686810115-ruriejj8olt099g99qajcllmijkd5d7n.apps.googleusercontent.com"
     data-callback="handleGoogleCredentialResponse">
</div>
<div class="g_id_signin" data-type="standard"></div>

<script>
  function handleGoogleCredentialResponse(response) {
    // response.credential IS the id_token - send it straight through.
    fetch("https://<backend-host>/auth/google", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id_token: response.credential }),
    })
      .then((res) => res.json())
      .then((data) => {
        if (data.access_token) {
          // store data.access_token the same way the password-login flow does
        }
      });
  }
</script>
```

If using a framework wrapper (`@react-oauth/google`, etc.) instead of the
raw script, the field to send is whatever that library calls the
**credential** / **id_token** from its success callback — same value.

### Registering the redirect origin (one-time Google Cloud Console step)

Whoever owns the Google Cloud project for this client ID needs to add the
frontend's actual domain(s) (e.g. `https://vstitch.example.com`, plus
`http://localhost:<port>` for local dev) under **Authorized JavaScript
origins** on that OAuth client. Without this, Google's own SDK will refuse
to issue a credential in the browser before it ever reaches this endpoint.

## Behavior notes for the frontend team

- **First-time Google sign-in** creates a new account automatically — no
  separate "register" step needed. A username is auto-generated from the
  email (e.g. `anjali.nanda@gmail.com` → `anjalinanda`, with a numeric
  suffix if that's taken).
- **Existing password account, same email** — signing in with Google
  links the Google account to that existing user rather than creating a
  duplicate. Same `vstitch_user_id` either way afterward.
- **Repeat Google sign-ins** always return the same `vstitch_user_id` —
  safe to call this endpoint every time the user clicks "Sign in with
  Google," no separate "is this a new user" check needed first.

---

## New: redirect flow (fixes Guest/Incognito sign-in)

The GIS widget above depends on the browser's FedCM API, which Chrome
**blocks by design** in Guest and Incognito profiles (`FedCM get() rejects
with NetworkError`). That's not fixable from either side's code — Google
recommends switching to the standard OAuth redirect flow instead, which
works everywhere. The backend now supports both; **please migrate the
"Sign in with Google" button to this flow** and we'll retire the GIS
widget once it's live.

### What changes for the frontend

Replace the GIS `<script>`/widget entirely. There is no JS SDK call and no
`id_token` to capture anymore — it's a plain navigation, like an `<a href>`.

**1. On button click, navigate the browser (not fetch/XHR) to:**
```
GET https://<backend-host>/auth/google/login
```
This redirects to Google's own login/consent screen. The backend handles
state/CSRF and the token exchange entirely server-side.

**2. After the user authenticates with Google**, they land back on:
```
<GOOGLE_POST_LOGIN_REDIRECT_URL>#token=<access_token>&token_type=bearer&vstitch_user_id=<id>&vstitch_user_name=<name>
```
(`GOOGLE_POST_LOGIN_REDIRECT_URL` is a backend env var we'll set to a page
on your domain, e.g. `https://vstichbyanjalinanda.com/account` — confirm
with us which route you want this to be.)

On that page, read the fragment (`window.location.hash`), pull out
`token`, and store/use it **exactly like the existing `access_token`** from
`POST /login` or `POST /auth/google` (same JWT shape, same `Authorization:
Bearer <token>` usage everywhere else). Then strip the hash from the URL
(`history.replaceState`) so the token doesn't linger in browser history.

Example:
```js
// on the post-login route
const params = new URLSearchParams(window.location.hash.slice(1));
const token = params.get("token");
if (token) {
  // store it the same way the password-login flow does
  window.history.replaceState(null, "", window.location.pathname);
}
```

**3. Error / cancel case** — Google or our backend may redirect back with
no `token` in the fragment (e.g. user closed the consent screen, or our
backend rejected an invalid `state`). Handle "no token present" on that
route as "sign-in failed, show the login page again" — there's no JSON
error body to read since this is a plain browser redirect, not a fetch.

### Not needed anymore for this flow

- No GIS `<script src="https://accounts.google.com/gsi/client">` tag.
- No `data-client_id` / `data-callback` widget markup.
- No `@react-oauth/google` (or similar) provider wrapping the app.
- No `credential`/`id_token` handling in frontend JS at all — the backend
  never gives the browser a raw Google credential in this flow.

### One-time Google Cloud Console step (backend team is handling this)

`https://vstichbyanjalinanda.com/auth/google/callback` needs to be added
under **Authorized redirect URIs** (not "JavaScript origins" — that's the
old flow) on the same OAuth client. Flagging here only so frontend knows
why local dev against this flow won't work until an equivalent localhost
redirect URI is registered too — ping backend if you need that for local
testing.
