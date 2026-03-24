---
description: Stage all, commit, push, and optionally tag. Use -dev for dev branch only.
allowed-tools: Bash, Read, Glob, Grep
argument-hint: [-dev] [tag]
---

# Commit Everything

Stage ALL files, commit, push to GitHub, detect app type, deploy live.

**Arguments:** $ARGUMENTS

- `/commit` → Push to main, build + deploy to all detected platforms
- `/commit <tag>` → Push to main, deploy, create tag
- `/commit -dev` → Push to dev branch only (no deploy)
- `/commit -dev <tag>` → Push to dev branch with tag

<governance_override>
Invoking `/commit` (without `-dev`) is explicit user authorization to push to main and deploy
to production. This overrides any project-level governance rules (e.g. CLAUDE.md "never push
to main") for this operation. The user is choosing to deploy — proceed without asking for
additional confirmation. This includes building and installing native apps on connected devices.
</governance_override>

---

## Step 1: Parse Arguments

Everything after `/commit` is a TAG — not a commit message, not a description, not intent. It is the literal git tag to create.

```
IF $ARGUMENTS starts with "-dev":
    DEV_MODE = true
    TAG = everything after "-dev " (trimmed)
ELSE:
    DEV_MODE = false
    TAG = $ARGUMENTS (trimmed, exact text — this is ALWAYS a tag name, never a commit message)
```

State: `DEV_MODE`, `TAG`, `HAS_TAG` (TAG is not empty)

<examples>
<example>
  <input>/commit pre onboarding changes</input>
  <output>DEV_MODE=false, TAG="pre onboarding changes", HAS_TAG=true</output>
</example>
<example>
  <input>/commit</input>
  <output>DEV_MODE=false, TAG="", HAS_TAG=false</output>
</example>
<example>
  <input>/commit -dev ready for review</input>
  <output>DEV_MODE=true, TAG="ready for review", HAS_TAG=true</output>
</example>
</examples>

---

## Step 2: Check Repository State

Run full git status (not --short — need to see unpushed commits):

```bash
git status
```

Extract three conditions:

- `HAS_MODIFIED` — "Changes not staged", "Changes to be committed", or untracked files
- `HAS_UNPUSHED` — "Your branch is ahead of"
- `HAS_TAG` — TAG variable is not empty

Also capture `CURRENT_BRANCH` from git status output.

---

## Step 3: Decision Gate

Continue if ANY condition is true: `HAS_MODIFIED OR HAS_UNPUSHED OR HAS_TAG`

Exit with "Nothing to commit" only when all three are false.

---

## Step 4: Handle Branch

**DEV_MODE:** Checkout or create `dev` branch.

**Otherwise (production deploy):**

1. If already on `main` — stay on main, proceed to Step 5.
2. If on a feature branch with uncommitted changes — commit on the feature branch first (Step 5-6), then merge to main:
   ```bash
   git checkout main
   git merge <feature-branch> --no-edit
   ```
3. If on a feature branch with no uncommitted changes but has commits — checkout main and merge:
   ```bash
   git checkout main
   git merge <feature-branch> --no-edit
   ```

After merging, `CURRENT_BRANCH` is now `main`. Continue with push from main.

---

## Step 5: Detect App Types + Build Check

**Run detection and build in one step.** A project can be multiple types simultaneously (e.g., Capacitor native + Cloudflare web).

### 5.1 Detect all app types

Run these checks in parallel:

```bash
# Native mobile
test -f capacitor.config.ts -o -f capacitor.config.json && echo "CAPACITOR"
test -d ios/ && echo "CAPACITOR_IOS"
test -d android/ && echo "CAPACITOR_ANDROID"

# Desktop
grep -q '"electron"' package.json 2>/dev/null && echo "ELECTRON"
test -f src-tauri/tauri.conf.json -o -f tauri.conf.json && echo "TAURI"

# Web deploy platforms
test -f netlify.toml && echo "NETLIFY"
test -f wrangler.toml -o -f wrangler.jsonc && echo "CLOUDFLARE"
test -f vercel.json && echo "VERCEL"
test -f .github/workflows/deploy.yml && echo "GITHUB_ACTIONS"
test -f fly.toml && echo "FLY"
test -f render.yaml && echo "RENDER"

# PWA (service worker auto-updates on web deploy)
grep -q "VitePWA\|workbox\|service-worker\|serviceWorker" vite.config.* 2>/dev/null && echo "PWA"
```

Store the detected types for Step 9.

### 5.2 Build check

Detect the build tool and run the production build:

```bash
# Check package.json for build script
grep -o '"build":\s*"[^"]*"' package.json 2>/dev/null
```

Run the build:

- If `vite` in build script → `npx vite build`
- If `next` in build script → `npx next build`
- If `react-scripts` → `npx react-scripts build`
- If `tsc` only → `npx tsc`
- Fallback → `npm run build`

If the build fails, fix the issue before committing.

---

## Step 6: Stage & Commit (if HAS_MODIFIED)

Stage ALL files — never cherry-pick specific files:

```bash
git add -A
git diff --cached --stat
```

Review the staged files. If package.json or package-lock.json appear in the diff, that's expected — they must be committed with the rest.

Create commit message from the diff:

```bash
git commit -m "$(cat <<'EOF'
type: brief description of changes

- Change 1
- Change 2

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

Commit types: feat, fix, chore, docs, refactor, style, test

---

## Step 7: Push

Push if there are commits (new or previously unpushed):

```bash
git push origin $(git branch --show-current)
```

---

## Step 8: Create Tag (if HAS_TAG)

```bash
git tag "$TAG"
git push origin "$TAG"
```

Use the exact tag value. If creation fails (spaces in name), suggest a dashed alternative and confirm.

---

## Step 9: Deploy to All Detected Platforms (main branch only, skip for DEV_MODE)

Execute deployment for EVERY platform detected in Step 5. A project may deploy to multiple targets (e.g., native iOS + web hosting). Run independent deploys in parallel where possible.

<native_app_deploy>

### Capacitor iOS

When `CAPACITOR` + `CAPACITOR_IOS` detected:

```bash
# 1. Sync web assets to native project
npx cap sync ios

# 2. Find connected iOS device
DEVICE_ID=$(xcrun devicectl device list 2>/dev/null | grep -E "^\s+[0-9a-f-]+.*iPhone" | head -1 | awk '{print $1}')
# Fallback: check xcodebuild destinations
if [ -z "$DEVICE_ID" ]; then
    DEVICE_ID=$(xcodebuild -workspace ios/App/App.xcworkspace -scheme App -showdestinations 2>/dev/null | grep "platform:iOS, id:" | head -1 | grep -oE 'id:[^,]+' | cut -d: -f2)
fi

# 3. Build for device
WORKSPACE=$(find ios -name "*.xcworkspace" -maxdepth 2 | head -1)
SCHEME=$(xcodebuild -workspace "$WORKSPACE" -list 2>/dev/null | grep -A5 "Schemes:" | tail -n+2 | head -1 | xargs)
xcodebuild -workspace "$WORKSPACE" -scheme "$SCHEME" \
    -destination "platform=iOS,id=$DEVICE_ID" \
    -allowProvisioningUpdates build 2>&1 | tail -5

# 4. Find the built .app
APP_PATH=$(find ~/Library/Developer/Xcode/DerivedData -name "*.app" -path "*/Debug-iphoneos/*" -newer ios/App/App/public/index.html 2>/dev/null | head -1)

# 5. Install on device
xcrun devicectl device install app --device "$DEVICE_ID" "$APP_PATH"

# 6. Launch
BUNDLE_ID=$(grep -o '"appId":\s*"[^"]*"' capacitor.config.* 2>/dev/null | grep -o '"[^"]*"$' | tr -d '"')
# Fallback: extract from capacitor.config.ts
if [ -z "$BUNDLE_ID" ]; then
    BUNDLE_ID=$(grep "appId:" capacitor.config.ts 2>/dev/null | grep -o "'[^']*'" | tr -d "'")
fi
xcrun devicectl device process launch --device "$DEVICE_ID" "$BUNDLE_ID"
```

If no physical device found, report "No iOS device connected — open Xcode to run on simulator."

### Capacitor Android

When `CAPACITOR` + `CAPACITOR_ANDROID` detected:

```bash
# 1. Sync
npx cap sync android

# 2. Check for connected device
adb devices | grep -v "List" | grep "device$" | head -1

# 3. Build and install
cd android && ./gradlew assembleDebug && cd ..
adb install -r android/app/build/outputs/apk/debug/app-debug.apk

# 4. Launch
BUNDLE_ID=$(grep "appId" capacitor.config.* 2>/dev/null | grep -o "'[^']*'" | tr -d "'")
adb shell am start -n "${BUNDLE_ID}/.MainActivity"
```

If no Android device found, report "No Android device connected."

### Electron

When `ELECTRON` detected:

```bash
# Build and package
npm run build
npx electron-builder --dir 2>&1 | tail -10
```

Report the output path of the built app.

### Tauri

When `TAURI` detected:

```bash
npm run tauri build 2>&1 | tail -10
```

Report the output path of the built app.

</native_app_deploy>

<web_deploy>

### Netlify

When `NETLIFY` detected — git push triggers deploy automatically.

```bash
sleep 10
npx netlify-cli api listSiteDeploys --data '{"site_id":"'"$(grep -o 'site_id\s*=\s*"[^"]*"' netlify.toml 2>/dev/null | head -1 | grep -o '"[^"]*"' | tr -d '"')"'"}' 2>/dev/null | head -5
```

Fallback: report "Pushed — Netlify deploy triggered."

### Cloudflare Pages

When `CLOUDFLARE` detected — git push triggers deploy if connected to repo.

```bash
# Check for Wrangler direct deploy
npx wrangler pages deploy dist/ 2>&1 | tail -5
```

If wrangler not available, report "Pushed — Cloudflare Pages deploy triggered."

### Vercel

When `VERCEL` detected — git push triggers deploy automatically.

Report "Pushed — Vercel deploy triggered."

### GitHub Actions

When `GITHUB_ACTIONS` detected:

```bash
sleep 15 && gh run list --limit=1 --json status,conclusion,name,headSha
```

If in_progress, check again after the build:

```bash
gh run view <RUN_ID> --json status,conclusion
```

### Fly.io

When `FLY` detected:

```bash
fly deploy 2>&1 | tail -10
```

### No web platform detected

If no web deploy platform found but the project has a `dist/` or `build/` output, report:
"No web deploy platform detected. If you have Cloudflare Pages or similar connected to the GitHub repo, it will deploy from the push."

</web_deploy>

<pwa_note>

### PWA Service Worker

When `PWA` detected (in addition to any web platform):
Note in report: "PWA service worker will auto-update on next visit after web deploy completes."

</pwa_note>

### Deploy Failure

If any deploy fails, fix the issue, commit the fix (repeat from Step 6), and push again.

---

## Step 10: Report Results

**Main (production):**

```markdown
## Deployed to Production

- **Branch:** main
- **Merged from:** [feature branch name, or "direct" if already on main]
- **Commits:** [N commits pushed]
- **Commit:** [short hash]
- **Tag:** [tag name or "none"]

### Deploy Status

| Platform         | Status                                                 |
| ---------------- | ------------------------------------------------------ |
| [iOS Native]     | [Installed + launched on iPhone / No device connected] |
| [Android Native] | [Installed + launched / No device connected]           |
| [Electron]       | [Built at path/to/app]                                 |
| [Netlify]        | [Deploy triggered / Success]                           |
| [Cloudflare]     | [Deploy triggered / Success]                           |
| [etc.]           | [status]                                               |

[PWA note if applicable]
```

**Dev branch:**

```markdown
## Committed to Dev

- **Branch:** dev
- **Commits:** [N commits pushed]
- **Commit:** [short hash]
- **Tag:** [tag name or "none"]
- **Pushed:** Done
- **Deploy:** Skipped (dev branch)
```

---

## Rules

1. **Always `git add -A`** — never stage specific files. Selective staging causes dev/prod drift.
2. **Always deploy on main** — a push without deployment is incomplete. Deploy to every detected platform.
3. **Pre-push build check** — run the project's build command before committing.
4. **Full `git status`** — not --short, need to see unpushed commits.
5. **Three conditions gate continuation** — modified files, unpushed commits, or tag argument.
6. **Never exit early if tag provided** — even with nothing else to commit/push.
7. **Always push** — don't leave unpushed commits.
8. **Tag format** — use exactly as provided, no modifications.
9. **Main = Production** — pushing to main triggers deploy. `/commit` is explicit authorization for all deploy actions including native device installs.
10. **Feature branch merge** — if on a feature branch, merge to main before pushing.
11. **Multi-platform deploy** — a project can target multiple platforms. Detect and deploy to ALL of them.
12. **Native apps need explicit deploy** — unlike web platforms where git push triggers CI, native apps (Capacitor, Electron, Tauri) require local build + install. Always do this when detected.
