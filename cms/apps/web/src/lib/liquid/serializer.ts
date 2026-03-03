/**
 * BlockTree → Liquid code serializer.
 */
import type { LiquidBlock, BlockTree } from "@/types/liquid-builder";

export function serializeLiquid(blocks: BlockTree, indent = ""): string {
  return blocks.map((block) => serializeBlock(block, indent)).join("");
}

function serializeBlock(block: LiquidBlock, indent: string): string {
  switch (block.type) {
    case "raw":
      return block.content;

    case "output":
      return `{{ ${block.expression} }}`;

    case "assign":
      return `{% assign ${block.name} = ${block.expression} %}`;

    case "if": {
      let result = `{% if ${block.condition} %}`;
      result += serializeLiquid(block.children, indent);
      if (block.elseChildren.length > 0) {
        result += `{% else %}`;
        result += serializeLiquid(block.elseChildren, indent);
      }
      result += `{% endif %}`;
      return result;
    }

    case "for": {
      let result = `{% for ${block.variable} in ${block.collection} %}`;
      result += serializeLiquid(block.children, indent);
      result += `{% endfor %}`;
      return result;
    }

    default:
      return "";
  }
}
