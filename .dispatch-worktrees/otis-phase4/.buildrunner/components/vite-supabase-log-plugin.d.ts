/**
 * BR3 Supabase Log Plugin - Vite Dev Server
 * Receives Supabase operation logs from the client-side supabaseLogger
 * and writes them to .buildrunner/supabase.log with auto-rotation.
 *
 * DEV-ONLY: configureServer() is a Vite dev-server hook — never
 * called during `vite build`, so zero production impact.
 *
 * READONLY — DO NOT MODIFY. Part of BR3 infrastructure.
 */
import type { Plugin } from 'vite';
export declare function supabaseLogPlugin(): Plugin;
export default supabaseLogPlugin;
