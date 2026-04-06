/**
 * BR3 Browser Logger - Vite Plugin
 *
 * Two log sources:
 *   1. LOCAL:  POST /__br_logger from the dev browser (same as before)
 *   2. PROD:   Supabase Realtime broadcast on channel "br-logs"
 *              (activated on prod via ?br_debug=1)
 *
 * Both write to .buildrunner/browser.log with auto-rotation.
 *
 * READONLY — DO NOT MODIFY unless explicitly fixing logging infrastructure.
 */
import type { Plugin } from 'vite';
export declare function brLoggerPlugin(): Plugin;
export default brLoggerPlugin;
