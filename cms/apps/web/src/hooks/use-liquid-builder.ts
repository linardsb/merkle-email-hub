"use client";

import { useState, useCallback, useRef } from "react";
import type { BlockTree, LiquidBlock } from "@/types/liquid-builder";
import { parseLiquid } from "@/lib/liquid/parser";
import { serializeLiquid } from "@/lib/liquid/serializer";

let blockIdCounter = 1000;
function newBlockId(): string {
  return `block-${++blockIdCounter}`;
}

export function useLiquidBuilder(initialCode?: string) {
  const [blocks, setBlocks] = useState<BlockTree>(() =>
    initialCode ? parseLiquid(initialCode) : []
  );
  const syncRef = useRef(false);

  /** Parse code string into block tree. */
  const parseFromCode = useCallback((code: string) => {
    syncRef.current = true;
    setBlocks(parseLiquid(code));
  }, []);

  /** Serialize block tree to code string. */
  const serializeToCode = useCallback((): string => {
    return serializeLiquid(blocks);
  }, [blocks]);

  /** Update a specific block by id. */
  const updateBlock = useCallback((id: string, updater: (block: LiquidBlock) => LiquidBlock) => {
    setBlocks((prev) => updateBlockInTree(prev, id, updater));
  }, []);

  /** Remove a block by id. */
  const removeBlock = useCallback((id: string) => {
    setBlocks((prev) => removeBlockFromTree(prev, id));
  }, []);

  /** Add a new block at the end. */
  const addBlock = useCallback((type: LiquidBlock["type"]) => {
    const block = createEmptyBlock(type);
    setBlocks((prev) => [...prev, block]);
  }, []);

  /** Reorder blocks via drag-and-drop. */
  const moveBlock = useCallback((activeId: string, overId: string) => {
    setBlocks((prev) => {
      const activeIdx = prev.findIndex((b) => b.id === activeId);
      const overIdx = prev.findIndex((b) => b.id === overId);
      if (activeIdx === -1 || overIdx === -1) return prev;
      const newBlocks = [...prev];
      const [moved] = newBlocks.splice(activeIdx, 1);
      newBlocks.splice(overIdx, 0, moved!);
      return newBlocks;
    });
  }, []);

  return {
    blocks,
    setBlocks,
    parseFromCode,
    serializeToCode,
    updateBlock,
    removeBlock,
    addBlock,
    moveBlock,
    syncRef,
  };
}

function createEmptyBlock(type: LiquidBlock["type"]): LiquidBlock {
  const id = newBlockId();
  switch (type) {
    case "if":
      return { id, type: "if", condition: "true", children: [], elseChildren: [] };
    case "for":
      return { id, type: "for", variable: "item", collection: "items", children: [] };
    case "assign":
      return { id, type: "assign", name: "variable", expression: "'value'" };
    case "output":
      return { id, type: "output", expression: "variable" };
    case "raw":
      return { id, type: "raw", content: "<p>HTML content</p>" };
  }
}

function updateBlockInTree(
  blocks: BlockTree,
  id: string,
  updater: (block: LiquidBlock) => LiquidBlock,
): BlockTree {
  return blocks.map((block) => {
    if (block.id === id) return updater(block);
    if (block.type === "if") {
      return {
        ...block,
        children: updateBlockInTree(block.children, id, updater),
        elseChildren: updateBlockInTree(block.elseChildren, id, updater),
      };
    }
    if (block.type === "for") {
      return {
        ...block,
        children: updateBlockInTree(block.children, id, updater),
      };
    }
    return block;
  });
}

function removeBlockFromTree(blocks: BlockTree, id: string): BlockTree {
  return blocks
    .filter((b) => b.id !== id)
    .map((block) => {
      if (block.type === "if") {
        return {
          ...block,
          children: removeBlockFromTree(block.children, id),
          elseChildren: removeBlockFromTree(block.elseChildren, id),
        };
      }
      if (block.type === "for") {
        return {
          ...block,
          children: removeBlockFromTree(block.children, id),
        };
      }
      return block;
    });
}
