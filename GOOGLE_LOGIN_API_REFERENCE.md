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
