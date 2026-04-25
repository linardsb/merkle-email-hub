"use client";

import { useState } from "react";
import { Popover, PopoverContent, PopoverTrigger } from "@email-hub/ui/components/ui/popover";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@email-hub/ui/components/ui/tooltip";

interface PaletteColorPickerProps {
  value: string;
  palette: { role: string; hex: string }[];
  onChange: (hex: string) => void;
}

export function PaletteColorPicker({ value, palette, onChange }: PaletteColorPickerProps) {
  const [open, setOpen] = useState(false);

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <button
          type="button"
          className="border-default h-8 w-8 rounded border shadow-sm transition-shadow hover:shadow-md"
          style={{ backgroundColor: value }}
          aria-label={`Color: ${value}`}
        />
      </PopoverTrigger>
      <PopoverContent className="w-48 p-2" align="start">
        <TooltipProvider delayDuration={200}>
          <div className="grid grid-cols-4 gap-1.5">
            {palette.map((swatch) => (
              <Tooltip key={swatch.role}>
                <TooltipTrigger asChild>
                  <button
                    type="button"
                    className={`h-8 w-8 rounded border transition-all ${
                      swatch.hex === value
                        ? "border-foreground ring-ring ring-2"
                        : "border-default hover:scale-110"
                    }`}
                    style={{ backgroundColor: swatch.hex }}
                    onClick={() => {
                      onChange(swatch.hex);
                      setOpen(false);
                    }}
                    aria-label={swatch.role}
                  />
                </TooltipTrigger>
                <TooltipContent side="bottom" className="text-xs">
                  <p>{swatch.role}</p>
                  <p className="text-muted-foreground">{swatch.hex}</p>
                </TooltipContent>
              </Tooltip>
            ))}
          </div>
        </TooltipProvider>
        {palette.length === 0 && (
          <p className="text-muted-foreground py-2 text-center text-xs">
            {"No palette colors configured"}
          </p>
        )}
      </PopoverContent>
    </Popover>
  );
}
