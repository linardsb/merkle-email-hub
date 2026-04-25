/**
 * Regex-based Liquid → BlockTree parser.
 * Handles if/elsif/else, for, assign, output, and raw HTML.
 */
import type { LiquidBlock, BlockTree } from "@/types/liquid-builder";

let idCounter = 0;
function nextId(): string {
  return `block-${++idCounter}`;
}

/** Reset counter (useful for tests). */
export function resetParser() {
  idCounter = 0;
}

export function parseLiquid(source: string): BlockTree {
  idCounter = 0;
  const blocks: BlockTree = [];
  let remaining = source;

  while (remaining.length > 0) {
    // Find next Liquid tag or output
    const tagMatch = remaining.match(
      /\{%-?\s*(if|for|assign|elsif|else|endif|endfor)\b([^%]*?)%\}|\{\{([^}]+)\}\}/,
    );

    if (!tagMatch) {
      // All remaining is raw HTML
      const trimmed = remaining.trim();
      if (trimmed) {
        blocks.push({ id: nextId(), type: "raw", content: remaining });
      }
      break;
    }

    const beforeTag = remaining.slice(0, tagMatch.index!);
    if (beforeTag.trim()) {
      blocks.push({ id: nextId(), type: "raw", content: beforeTag });
    }

    remaining = remaining.slice(tagMatch.index! + tagMatch[0].length);

    // Output tag {{ expression }}
    if (tagMatch[3]) {
      blocks.push({ id: nextId(), type: "output", expression: tagMatch[3].trim() });
      continue;
    }

    const keyword = tagMatch[1]!;
    const args = tagMatch[2]?.trim() ?? "";

    if (keyword === "assign") {
      const assignMatch = args.match(/^(\w+)\s*=\s*(.+)$/);
      if (assignMatch) {
        blocks.push({
          id: nextId(),
          type: "assign",
          name: assignMatch[1]!,
          expression: assignMatch[2]!.trim(),
        });
      }
      continue;
    }

    if (keyword === "if") {
      const { block, rest } = parseIf(args, remaining);
      blocks.push(block);
      remaining = rest;
      continue;
    }

    if (keyword === "for") {
      const forMatch = args.match(/^(\w+)\s+in\s+(.+)$/);
      const variable = forMatch?.[1] ?? "item";
      const collection = forMatch?.[2]?.trim() ?? "items";
      const { children, rest } = parseUntilEndFor(remaining);
      blocks.push({ id: nextId(), type: "for", variable, collection, children });
      remaining = rest;
      continue;
    }

    // elsif/else/endif/endfor outside context — skip
  }

  return blocks;
}

function parseIf(condition: string, source: string): { block: LiquidBlock; rest: string } {
  const children: LiquidBlock[] = [];
  const elseChildren: LiquidBlock[] = [];
  let inElse = false;
  let remaining = source;
  let depth = 0;

  while (remaining.length > 0) {
    const tagMatch = remaining.match(/\{%-?\s*(if|elsif|else|endif)\b([^%]*?)%\}|\{\{([^}]+)\}\}/);

    if (!tagMatch) {
      const target = inElse ? elseChildren : children;
      if (remaining.trim()) {
        target.push({ id: nextId(), type: "raw", content: remaining });
      }
      remaining = "";
      break;
    }

    const before = remaining.slice(0, tagMatch.index!);
    if (before.trim()) {
      const target = inElse ? elseChildren : children;
      target.push({ id: nextId(), type: "raw", content: before });
    }

    remaining = remaining.slice(tagMatch.index! + tagMatch[0].length);

    // Output
    if (tagMatch[3]) {
      const target = inElse ? elseChildren : children;
      target.push({ id: nextId(), type: "output", expression: tagMatch[3].trim() });
      continue;
    }

    const kw = tagMatch[1]!;

    if (kw === "if") {
      depth++;
      // Nested if — treat as raw for simplicity at this parsing level
      const target = inElse ? elseChildren : children;
      target.push({ id: nextId(), type: "raw", content: tagMatch[0] });
      continue;
    }

    if (kw === "endif") {
      if (depth > 0) {
        depth--;
        const target = inElse ? elseChildren : children;
        target.push({ id: nextId(), type: "raw", content: tagMatch[0] });
        continue;
      }
      // This ends our if block
      break;
    }

    if (kw === "else" && depth === 0) {
      inElse = true;
      continue;
    }

    if (kw === "elsif" && depth === 0) {
      // Treat elsif as else with embedded condition (simplified)
      inElse = true;
      continue;
    }
  }

  return {
    block: { id: nextId(), type: "if", condition, children, elseChildren },
    rest: remaining,
  };
}

function parseUntilEndFor(source: string): { children: LiquidBlock[]; rest: string } {
  const children: LiquidBlock[] = [];
  let remaining = source;
  let depth = 0;

  while (remaining.length > 0) {
    const tagMatch = remaining.match(/\{%-?\s*(for|endfor)\b([^%]*?)%\}|\{\{([^}]+)\}\}/);

    if (!tagMatch) {
      if (remaining.trim()) {
        children.push({ id: nextId(), type: "raw", content: remaining });
      }
      remaining = "";
      break;
    }

    const before = remaining.slice(0, tagMatch.index!);
    if (before.trim()) {
      children.push({ id: nextId(), type: "raw", content: before });
    }

    remaining = remaining.slice(tagMatch.index! + tagMatch[0].length);

    if (tagMatch[3]) {
      children.push({ id: nextId(), type: "output", expression: tagMatch[3].trim() });
      continue;
    }

    if (tagMatch[1] === "for") {
      depth++;
      children.push({ id: nextId(), type: "raw", content: tagMatch[0] });
      continue;
    }

    if (tagMatch[1] === "endfor") {
      if (depth > 0) {
        depth--;
        children.push({ id: nextId(), type: "raw", content: tagMatch[0] });
        continue;
      }
      break;
    }
  }

  return { children, rest: remaining };
}
