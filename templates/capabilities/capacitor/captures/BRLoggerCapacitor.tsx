import { useEffect } from "react";

import { installCapacitorCapture } from "./capacitorCapture";

export function BRLoggerCapacitor(): null {
  useEffect(() => {
    installCapacitorCapture();
  }, []);

  return null;
}

export default BRLoggerCapacitor;
