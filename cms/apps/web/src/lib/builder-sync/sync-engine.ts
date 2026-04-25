import type { SectionNode, SyncStatus } from "@/types/visual-builder";
import { htmlToSections, sectionsToHtml } from "./ast-mapper";

export interface SyncEngineCallbacks {
  onBuilderUpdate: (sections: SectionNode[]) => void;
  onCodeUpdate: (html: string) => void;
  onStatusChange: (status: SyncStatus) => void;
  onParseError: (error: string) => void;
}

/**
 * Manages bidirectional sync between code editor and visual builder.
 *
 * - code -> builder: debounced at 500ms (parsing is expensive)
 * - builder -> code: debounced at 200ms (serialization is fast)
 * - Conflict: if both change within debounce window, builder wins (last-write-wins)
 */
export class BuilderSyncEngine {
  private callbacks: SyncEngineCallbacks;
  private codeTimer: ReturnType<typeof setTimeout> | null = null;
  private builderTimer: ReturnType<typeof setTimeout> | null = null;
  private lastCodeHtml: string = "";
  private lastBuilderSections: SectionNode[] = [];
  private templateShell: string = "";
  private syncing = false;

  constructor(callbacks: SyncEngineCallbacks) {
    this.callbacks = callbacks;
  }

  /** Called when the code editor content changes */
  onCodeChange(html: string): void {
    if (this.syncing) return;
    this.lastCodeHtml = html;

    if (this.codeTimer) clearTimeout(this.codeTimer);
    this.callbacks.onStatusChange("syncing");

    this.codeTimer = setTimeout(() => {
      this.syncCodeToBuilder(html);
    }, 500);
  }

  /** Called when the builder sections change */
  onBuilderChange(sections: SectionNode[]): void {
    if (this.syncing) return;
    this.lastBuilderSections = sections;

    // Cancel any pending code -> builder sync (builder wins)
    if (this.codeTimer) {
      clearTimeout(this.codeTimer);
      this.codeTimer = null;
    }

    if (this.builderTimer) clearTimeout(this.builderTimer);
    this.callbacks.onStatusChange("syncing");

    this.builderTimer = setTimeout(() => {
      this.syncBuilderToCode(sections);
    }, 200);
  }

  /** Set the template shell (wrapper HTML around sections) */
  setTemplateShell(shell: string): void {
    this.templateShell = shell;
  }

  /** Clean up timers */
  dispose(): void {
    if (this.codeTimer) clearTimeout(this.codeTimer);
    if (this.builderTimer) clearTimeout(this.builderTimer);
  }

  private syncCodeToBuilder(html: string): void {
    this.syncing = true;
    try {
      const sections = htmlToSections(html);
      if (sections === null) {
        this.callbacks.onStatusChange("parse_error");
        this.callbacks.onParseError(
          "HTML structure could not be parsed into sections. The code editor remains functional.",
        );
        return;
      }
      // Only update template shell after a successful parse
      if (html.includes("<html")) {
        this.templateShell = html;
      }
      this.lastBuilderSections = sections;
      this.callbacks.onBuilderUpdate(sections);
      this.callbacks.onStatusChange("synced");
    } finally {
      this.syncing = false;
    }
  }

  private syncBuilderToCode(sections: SectionNode[]): void {
    this.syncing = true;
    try {
      const html = sectionsToHtml(sections, this.templateShell || this.lastCodeHtml);
      this.lastCodeHtml = html;
      this.callbacks.onCodeUpdate(html);
      this.callbacks.onStatusChange("synced");
    } finally {
      this.syncing = false;
    }
  }
}
