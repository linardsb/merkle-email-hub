"use client";

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@email-hub/ui/components/ui/dropdown-menu";
import { toast } from "sonner";
import { hexToRgbString, hexToHslString } from "@/lib/color-utils";

interface ColorContextMenuProps {
  hex: string;
  name: string;
  children: React.ReactNode;
}

export function ColorContextMenu({ hex, name, children }: ColorContextMenuProps) {
  const copyAndNotify = async (value: string, label: string) => {
    await navigator.clipboard.writeText(value);
    toast.success(`${label} copied to clipboard`);
  };

  const varName = `--${name.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`;

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>{children}</DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="w-56">
        <DropdownMenuItem onClick={() => copyAndNotify(hex, "HEX")}>
          HEX: {hex}
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => copyAndNotify(hexToRgbString(hex), "RGB")}>
          RGB: {hexToRgbString(hex)}
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => copyAndNotify(hexToHslString(hex), "HSL")}>
          HSL: {hexToHslString(hex)}
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => copyAndNotify(`var(${varName})`, "CSS var")}>
          CSS var: var({varName})
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={() => copyAndNotify(`text-[${hex}]`, "Tailwind text")}>
          text-[{hex}]
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => copyAndNotify(`bg-[${hex}]`, "Tailwind bg")}>
          bg-[{hex}]
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => copyAndNotify(`border-[${hex}]`, "Tailwind border")}>
          border-[{hex}]
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

interface FontContextMenuProps {
  family: string;
  weight: string;
  size: number;
  lineHeight: number;
  children: React.ReactNode;
}

export function FontContextMenu({
  family,
  weight,
  size,
  lineHeight,
  children,
}: FontContextMenuProps) {
  const copyAndNotify = async (value: string, label: string) => {
    await navigator.clipboard.writeText(value);
    toast.success(`${label} copied to clipboard`);
  };

  const cssShorthand = `font: ${weight} ${size}px/${lineHeight}px '${family}'`;
  const escapedFamily = family.replace(/ /g, "_");

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>{children}</DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="w-64">
        <DropdownMenuItem onClick={() => copyAndNotify(`font-family: '${family}';`, "font-family")}>
          font-family: &apos;{family}&apos;;
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => copyAndNotify(cssShorthand, "CSS shorthand")}>
          {cssShorthand}
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={() => copyAndNotify(`font-['${escapedFamily}']`, "Tailwind font")}>
          font-[&apos;{escapedFamily}&apos;]
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => copyAndNotify(`text-[${size}px]`, "Tailwind size")}>
          text-[{size}px]
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => copyAndNotify(`leading-[${lineHeight}px]`, "Tailwind leading")}>
          leading-[{lineHeight}px]
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
