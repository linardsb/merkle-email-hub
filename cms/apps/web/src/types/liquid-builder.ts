export type LiquidBlockType = "if" | "for" | "assign" | "output" | "raw";

export interface IfBlock {
  id: string;
  type: "if";
  condition: string;
  children: LiquidBlock[];
  elseChildren: LiquidBlock[];
}

export interface ForBlock {
  id: string;
  type: "for";
  variable: string;
  collection: string;
  children: LiquidBlock[];
}

export interface AssignBlock {
  id: string;
  type: "assign";
  name: string;
  expression: string;
}

export interface OutputBlock {
  id: string;
  type: "output";
  expression: string;
}

export interface RawBlock {
  id: string;
  type: "raw";
  content: string;
}

export type LiquidBlock = IfBlock | ForBlock | AssignBlock | OutputBlock | RawBlock;

export type BlockTree = LiquidBlock[];
