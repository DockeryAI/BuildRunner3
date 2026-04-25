import { Capacitor } from "@capacitor/core";

let installed = false;

export function installCapacitorCapture(): void {
  if (installed) {
    return;
  }

  installed = true;
  const platform = Capacitor.getPlatform();

  window.addEventListener("error", (event) => {
    console.error("[BRLoggerCapacitor:error]", {
      platform,
      message: event.message,
      filename: event.filename,
      line: event.lineno,
      column: event.colno,
    });
  });

  window.addEventListener("unhandledrejection", (event) => {
    console.error("[BRLoggerCapacitor:promise]", {
      platform,
      reason: event.reason,
    });
  });

  console.info("[BRLoggerCapacitor] capture installed", {
    platform,
    nativePlatform: Capacitor.isNativePlatform(),
  });
}
