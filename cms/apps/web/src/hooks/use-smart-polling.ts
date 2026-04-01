import { useEffect, useState } from "react";

type VisibilityState = "visible" | "hidden" | "blurred";

/**
 * Visibility-aware polling interval for SWR.
 * - visible: baseInterval (full speed)
 * - blurred: baseInterval * 1.5 (window unfocused but tab visible)
 * - hidden: 0 (paused — tab not visible)
 *
 * Usage: useSWR(key, fetcher, { refreshInterval: useSmartPolling(3000) })
 */
export function useSmartPolling(baseInterval: number): number {
  const [visibility, setVisibility] = useState<VisibilityState>("visible");

  useEffect(() => {
    const onVisibilityChange = () => {
      setVisibility(document.hidden ? "hidden" : "visible");
    };
    const onFocus = () => setVisibility("visible");
    const onBlur = () => {
      if (!document.hidden) setVisibility("blurred");
    };

    document.addEventListener("visibilitychange", onVisibilityChange);
    window.addEventListener("focus", onFocus);
    window.addEventListener("blur", onBlur);

    return () => {
      document.removeEventListener("visibilitychange", onVisibilityChange);
      window.removeEventListener("focus", onFocus);
      window.removeEventListener("blur", onBlur);
    };
  }, []);

  if (baseInterval === 0) return 0;

  switch (visibility) {
    case "visible":
      return baseInterval;
    case "blurred":
      return Math.round(baseInterval * 1.5);
    case "hidden":
      return 0;
  }
}
