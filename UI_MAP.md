# Qwen Cloud UI Map

End-to-end mapping via Playwright MCP (2026-06-26).

## Flow

```
https://home.qwencloud.com/
  → redirects to account.alibabacloud.com/sso/login.htm (Log In - Qwen Cloud)
  → click "Sign Up" link
  → /sso/register (Sign Up - Qwen Cloud)
  → fill email → click "Next"
  → OTP verification page (6 digit inputs)
  → type code → auto-advance or click "Validate"
  → country selection page (combobox + checkbox + Continue)
  → dashboard (home.qwencloud.com)
  → /api-keys → "Create API key" button
  → dialog "Create API Key" → fill description → "Generate Key"
  → dialog "Copy your API Key" → extract sk-ws-... from textbox
```

## Selectors

### 1. Login Page (`/sso/login`)
- **Title**: `Log In - Qwen Cloud`
- **Email input**: `textbox "Email"` → `input[placeholder="Email"]`
- **Next button**: `button "Next"` (disabled until email filled)
- **Sign Up link**: `link "Sign Up"` → `a:has-text("Sign Up")`
- **Google/Github buttons**: `button "Log in with Google"` / `button "Log in with Github"`

### 2. Signup Email Page (`/sso/register`)
- **Title**: `Sign Up - Qwen Cloud`
- **Heading**: `Sign Up` (text)
- **Email input**: `textbox "Email"` → `input[placeholder="Email"]`
- **Next button**: `button "Next"` (disabled until email typed) → `button:has-text("Next")`
- **Google/Github buttons**: `button "Sign up with Google"` / `button "Sign up with Github"`
- **Log In link**: `link "Log In"` (back to login)

### 3. OTP Verification Page
- **Heading**: `Enter Verification Code`
- **Info text**: `We've sent a verification code to {email}. Please enter the code below.`
- **OTP inputs**: 6× `textbox` (maxlength=1, inputmode=numeric)
  - CSS: `input[type="text"]` (first one receives all 6 digits via `press_sequentially`)
  - Auto-advances between boxes; auto-submits after 6th digit
- **Validate button**: `button "Validate"` (disabled until all 6 filled) → `button:has-text("Validate")`
- **Resend text**: `Resend in Xs` (countdown) or `Resend Code` (ready)
- **Error messages**: `Invalid verification code`, `Verification code is not ready. Please wait for the code to be sent.`

### 4. Country Selection Page
- **Heading**: `Sign Up`
- **Instruction**: `Almost there! Please select your country/region. This determines your currency and tax and cannot be changed later.`
- **Country combobox**: `combobox "Select your country/region"` → `input[placeholder="Select your country/region"]`
  - Click to open → type country name → options appear in `listbox`
- **Country option**: `option "CountryName"` → `[role="option"]:has-text("Country")`
  - Fallback: JS `Array.from(document.querySelectorAll('[role=option]')).find(el => el.innerText.includes('Country'))`
- **Agreement checkbox**: `checkbox "I hereby agree to the Qwen Cloud Website Customer Agreement, Privacy Policy, and Terms of Use."`
  - CSS: `input[type="checkbox"]`
  - JS click required: `cb.click()` triggers React onChange (Playwright force click does NOT work)
- **Continue button**: `button "Continue"` (disabled until country + checkbox) → `button:has-text("Continue")`

### 5. Dashboard (`home.qwencloud.com`)
- **Title**: `Home - Console - Qwen Cloud`
- **URL pattern**: `https://home.qwencloud.com/`
- **Navigation**: sidebar with Home, Try AI, Analytics, Billing, Model Production, API Keys, Settings

### 6. API Keys Page (`home.qwencloud.com/api-keys`)
- **Title**: `API Keys - Console - Qwen Cloud`
- **Mobile overlay**: generic notification with text `mobile devices` + Close button
  - Dismiss: click first `button` inside the notification
- **Create API key button**: `button "Create API key"` → `button:has-text("Create API key")`
- **Base URL display** (read-only textboxes):
  - OpenAI Compatible: `https://dashscope-intl.aliyuncs.com/compatible-mode/v1`
  - Anthropic Compatible: `https://dashscope-intl.aliyuncs.com/apps/anthropic`

### 7. Create API Key Dialog
- **Dialog**: `dialog "Create API Key"`
- **Heading**: `Create API Key` (h2)
- **Description textbox**: `textbox "e.g., Production API key for main application"` → `input[placeholder*="Production API key"]`
  - Character limit: 0/50
- **Generate Key button**: `button "Generate Key"` (disabled until description filled) → `button:has-text("Generate Key")`
- **Cancel button**: `button "Cancel"`

### 8. Copy API Key Dialog
- **Dialog**: `dialog "Copy your API Key"`
- **Heading**: `Copy your API Key` (h2)
- **API key textbox**: `textbox` containing `sk-ws-...` → `dialog input` (first input)
- **Copy to clipboard button**: `button "Copy to clipboard"`
- **Close button**: `button "Close"`
- **Warning**: `This value is viewable one time only`

## Verification Email

- **Sender**: `Qwen Cloud <system_sg@notice.qwencloud.com>`
- **Subject**: `Verification Code from Qwen Cloud`
- **To header**: Contains the exact variant email used at signup
- **Code location**: `<div style="font-size: 36px; font-weight: bold; color: #333333; ...">CODE</div>`
- **Label text**: `Your verification code for Qwen Cloud is:` (some emails omit "Your")
- **Regex (flexible)**: `(?:Your )?verification code for Qwen Cloud is:.*?<div[^>]*>\s*(\d{6})\s*</div>`
- **Fallback regex**: `<div[^>]*font-size:\s*36px[^>]*>\s*(\d{6})\s*</div>`
- **Filter**: Must check `internalDate > request_time_ms` to avoid stale codes
- **Filter**: Must check `To` header or body contains the signup email variant

## Key Notes

1. **OTP auto-advance**: Typing all 6 digits into the first input via `press_sequentially` auto-fills remaining boxes and may auto-submit. If not, click `Validate`.
2. **Checkbox**: React component requires JS `.click()` on the input element, not Playwright `.click(force=True)`.
3. **Navigation race**: After clicking `Continue`, `page.title()` or `page.url` may throw `Execution context was destroyed` — wrap in try/except.
4. **Proxy**: Must pass as `{server, username, password}` dict, not URL string.
5. **Country list**: Full list of ~170 countries. Common ones in `COUNTRIES` array.
