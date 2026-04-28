"use client";

import { useState } from "react";

/**
 * Centralizes the six workspace dialog open/close booleans. Returns each as
 * a named state pair so call sites read more naturally than indexing into a
 * keyed object.
 */
export function useWorkspaceDialogs() {
  const [exportOpen, setExportOpen] = useState(false);
  const [imageGenOpen, setImageGenOpen] = useState(false);
  const [briefOpen, setBriefOpen] = useState(false);
  const [blueprintOpen, setBlueprintOpen] = useState(false);
  const [pushOpen, setPushOpen] = useState(false);
  const [approvalOpen, setApprovalOpen] = useState(false);

  return {
    exportOpen,
    setExportOpen,
    imageGenOpen,
    setImageGenOpen,
    briefOpen,
    setBriefOpen,
    blueprintOpen,
    setBlueprintOpen,
    pushOpen,
    setPushOpen,
    approvalOpen,
    setApprovalOpen,
  };
}
