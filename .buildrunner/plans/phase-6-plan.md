# Phase 6 Plan: Account Swap Fix + Usage Warning

## Health Check Findings

**Root cause of swap failures:** Claude Code refreshes OAuth tokens during use. Backup keychain entries become stale. Swapping restores expired tokens.

**Token format:** JSON with accessToken, refreshToken, expiresAt, scopes, subscriptionType, rateLimitTier.

## Tasks

### 6.1: Fix br-swap-accounts.sh — save current token before overwriting
### 6.2: Add token validation to br-account-setup.sh
### 6.3: Create usage-monitor.sh
### 6.4: Create usage-check.sh hook
