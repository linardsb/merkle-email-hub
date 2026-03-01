import type * as Monaco from "monaco-editor";

let registered = false;

export function registerMaizzleLanguage(monaco: typeof Monaco): void {
  if (registered) return;
  registered = true;

  monaco.languages.register({ id: "maizzle" });

  monaco.languages.setMonarchTokensProvider("maizzle", {
    defaultToken: "",
    ignoreCase: true,

    maizzleTags: [
      "extends",
      "block",
      "component",
      "slot",
      "fill",
      "stack",
      "push",
      "each",
      "if",
      "elseif",
      "else",
      "switch",
      "case",
      "default",
      "raw",
      "markdown",
      "outlook",
      "not-outlook",
    ],

    liquidKeywords: [
      "if",
      "elsif",
      "else",
      "endif",
      "unless",
      "endunless",
      "for",
      "endfor",
      "case",
      "when",
      "endcase",
      "assign",
      "capture",
      "endcapture",
      "comment",
      "endcomment",
      "include",
      "render",
      "raw",
      "endraw",
      "tablerow",
      "endtablerow",
      "break",
      "continue",
      "cycle",
      "increment",
      "decrement",
    ],

    tokenizer: {
      root: [
        // YAML front matter
        [/^---\s*$/, { token: "comment.yaml", next: "@yamlFrontMatter" }],

        // Maizzle expression {{{ }}}
        [/\{\{\{/, { token: "delimiter.liquid", next: "@maizzleExpression" }],

        // Liquid output {{ }}
        [/\{\{-?/, { token: "delimiter.liquid", next: "@liquidOutput" }],

        // Liquid tag {% %}
        [/\{%-?/, { token: "delimiter.liquid", next: "@liquidTag" }],

        // MSO conditional comments
        [
          /<!--\[if\s+(?:mso|gte\s+mso|lte\s+mso|gt\s+mso|lt\s+mso).*?\]>/,
          "comment.mso",
        ],
        [/<!\[endif\]-->/, "comment.mso"],

        // HTML comments
        [/<!--/, "comment.html", "@comment"],

        // Maizzle tags
        [
          /(<)(extends|block|component|slot|fill|stack|push|each|outlook|not-outlook)\b/,
          [
            { token: "delimiter.html" },
            { token: "tag.maizzle", next: "@tag" },
          ],
        ],
        [
          /(<\/)(extends|block|component|slot|fill|stack|push|each|outlook|not-outlook)\b/,
          [
            { token: "delimiter.html" },
            { token: "tag.maizzle", next: "@tag" },
          ],
        ],

        // HTML tags
        [/<\/?/, { token: "delimiter.html", next: "@tag" }],

        // Entities
        [/&\w+;/, "string.html.entity"],
      ],

      yamlFrontMatter: [
        [/^---\s*$/, { token: "comment.yaml", next: "@pop" }],
        [/[^-]+/, "comment.yaml"],
        [/-/, "comment.yaml"],
      ],

      maizzleExpression: [
        [/\}\}\}/, { token: "delimiter.liquid", next: "@pop" }],
        [/"[^"]*"/, "string.liquid"],
        [/'[^']*'/, "string.liquid"],
        [/\|/, "delimiter.liquid"],
        [/[a-zA-Z_]\w*/, "variable.liquid"],
        [/./, "variable.liquid"],
      ],

      liquidOutput: [
        [/-?\}\}/, { token: "delimiter.liquid", next: "@pop" }],
        [/"[^"]*"/, "string.liquid"],
        [/'[^']*'/, "string.liquid"],
        [/\|/, "delimiter.liquid"],
        [
          /[a-zA-Z_][\w.]*/,
          {
            cases: {
              "true|false|nil|null|blank|empty": "keyword.liquid",
              "@default": "variable.liquid",
            },
          },
        ],
        [/\d+(\.\d+)?/, "number.liquid"],
        [/./, "variable.liquid"],
      ],

      liquidTag: [
        [/-?%\}/, { token: "delimiter.liquid", next: "@pop" }],
        [/"[^"]*"/, "string.liquid"],
        [/'[^']*'/, "string.liquid"],
        [
          /[a-zA-Z_]\w*/,
          {
            cases: {
              "@liquidKeywords": "keyword.liquid",
              "true|false|nil|null|blank|empty": "keyword.liquid",
              "and|or|not|contains|in": "keyword.liquid",
              "@default": "variable.liquid",
            },
          },
        ],
        [/[=!<>]=?|!=/, "operator.liquid"],
        [/\d+(\.\d+)?/, "number.liquid"],
        [/./, "variable.liquid"],
      ],

      tag: [
        [/\/?>/, { token: "delimiter.html", next: "@pop" }],
        // Liquid inside attributes
        [/\{\{-?/, { token: "delimiter.liquid", next: "@liquidOutput" }],
        [/\{%-?/, { token: "delimiter.liquid", next: "@liquidTag" }],
        // Attributes
        [/[a-zA-Z_][\w-]*/, "attribute.name.html"],
        [/=/, "delimiter.html"],
        [/"[^"]*"/, "attribute.value.html"],
        [/'[^']*'/, "attribute.value.html"],
        [/\s+/, ""],
      ],

      comment: [
        [/-->/, "comment.html", "@pop"],
        [/./, "comment.html"],
      ],
    },
  });

  monaco.languages.setLanguageConfiguration("maizzle", {
    comments: {
      blockComment: ["<!--", "-->"],
    },
    brackets: [
      ["<!--", "-->"],
      ["<", ">"],
      ["{", "}"],
      ["{{", "}}"],
      ["{%", "%}"],
      ["{{{", "}}}"],
    ],
    autoClosingPairs: [
      { open: "{", close: "}" },
      { open: "[", close: "]" },
      { open: "(", close: ")" },
      { open: '"', close: '"' },
      { open: "'", close: "'" },
      { open: "<!--", close: "-->" },
      { open: "{{", close: "}}" },
      { open: "{%", close: "%}" },
      { open: "{{{", close: "}}}" },
    ],
    surroundingPairs: [
      { open: "<", close: ">" },
      { open: '"', close: '"' },
      { open: "'", close: "'" },
    ],
    folding: {
      markers: {
        start: /^\s*<!--\s*#region\b/,
        end: /^\s*<!--\s*#endregion\b/,
      },
    },
    indentationRules: {
      increaseIndentPattern:
        /<(?!area|base|br|col|embed|hr|img|input|keygen|link|meta|param|source|track|wbr)(\w[\w-]*)[^/]*[^/]>\s*$/,
      decreaseIndentPattern: /^\s*<\/\w/,
    },
  });

  monaco.languages.registerCompletionItemProvider("maizzle", {
    provideCompletionItems(model, position) {
      const word = model.getWordUntilPosition(position);
      const range = {
        startLineNumber: position.lineNumber,
        endLineNumber: position.lineNumber,
        startColumn: word.startColumn,
        endColumn: word.endColumn,
      };

      return {
        suggestions: [
          {
            label: "<extends>",
            kind: monaco.languages.CompletionItemKind.Snippet,
            insertText: '<extends src="${1:src/layouts/main.html}">\n\t$0\n</extends>',
            insertTextRules:
              monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
            documentation: "Maizzle layout extends",
            range,
          },
          {
            label: "<block>",
            kind: monaco.languages.CompletionItemKind.Snippet,
            insertText: '<block name="${1:content}">\n\t$0\n</block>',
            insertTextRules:
              monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
            documentation: "Maizzle content block",
            range,
          },
          {
            label: "<component>",
            kind: monaco.languages.CompletionItemKind.Snippet,
            insertText: '<component src="${1:src/components/}">\n\t$0\n</component>',
            insertTextRules:
              monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
            documentation: "Maizzle component include",
            range,
          },
          {
            label: "{{ }}",
            kind: monaco.languages.CompletionItemKind.Snippet,
            insertText: "{{ ${1:variable} }}",
            insertTextRules:
              monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
            documentation: "Liquid output tag",
            range,
          },
          {
            label: "{% if %}",
            kind: monaco.languages.CompletionItemKind.Snippet,
            insertText: "{% if ${1:condition} %}\n\t$0\n{% endif %}",
            insertTextRules:
              monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
            documentation: "Liquid if block",
            range,
          },
          {
            label: "{% for %}",
            kind: monaco.languages.CompletionItemKind.Snippet,
            insertText:
              "{% for ${1:item} in ${2:collection} %}\n\t$0\n{% endfor %}",
            insertTextRules:
              monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
            documentation: "Liquid for loop",
            range,
          },
          {
            label: "<!--[if mso]>",
            kind: monaco.languages.CompletionItemKind.Snippet,
            insertText: "<!--[if mso]>\n$0\n<![endif]-->",
            insertTextRules:
              monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
            documentation: "MSO conditional comment for Outlook",
            range,
          },
        ],
      };
    },
  });
}
