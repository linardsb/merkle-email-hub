"use client";

import Image from "next/image";
import { Paintbrush } from "../icons";
import type { DesignProvider } from "@/types/design-sync";

interface ProviderIconProps {
  provider: DesignProvider;
  className?: string;
}

export function ProviderIcon({ provider, className = "h-5 w-5" }: ProviderIconProps) {
  if (provider === "figma") {
    return (
      <Image
        src="/icons/brand/figma.svg"
        alt="Figma"
        width={20}
        height={20}
        className={className}
      />
    );
  }
  // Sketch and Canva use a generic icon for now
  return <Paintbrush className={`${className} text-foreground-muted`} />;
}
