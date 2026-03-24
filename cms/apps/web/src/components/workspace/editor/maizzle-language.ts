import type { languages } from "monaco-editor";

export const LANGUAGE_ID = "maizzle-html";

export const monarchTokensProvider: languages.IMonarchLanguage = {
  defaultToken: "",
  ignoreCase: true,
  tokenizer: {
    root: [
      [/^---\s*$/, { token: "meta", next: "@yamlFrontMatter" }],
      [/\{\{\{/, { token: "delimiter.expression", next: "@maizzleExpr" }],
      [/\{\{-?/, { token: "delimiter.expression", next: "@liquidOutput" }],
      [/\{%-?/, { token: "delimiter.expression", next: "@liquidTag" }],
      [/<!--\[if\s+(?:mso|gte\s+mso|lte\s+mso|gt\s+mso|lt\s+mso)[^\]]*\]>/, "comment"],
      [/<!\[endif\]-->/, "comment"],
      [/<!--/, { token: "comment", next: "@htmlComment" }],
      [/<\/?(extends|block|component|slot|fill|stack|push|each|if|elseif|else|switch|case|default|raw|markdown|outlook|not-outlook)(?=[\s/>])/, "tag.maizzle"],
      [/<\/?/, { token: "delimiter.html", next: "@htmlTag" }],
      [/&\w+;/, "string.escape"],
      [/[^<{&]+/, ""],
    ],
    yamlFrontMatter: [
      [/^---\s*$/, { token: "meta", next: "@pop" }],
      [/.*/, "meta.content"],
    ],
    maizzleExpr: [
      [/\}\}\}/, { token: "delimiter.expression", next: "@pop" }],
      [/"[^"]*"|'[^']*'/, "string"],
      [/\|/, "delimiter"],
      [/[a-zA-Z_]\w*/, "variable"],
      [/./, "variable"],
    ],
    liquidOutput: [
      [/-?\}\}/, { token: "delimiter.expression", next: "@pop" }],
      [/"[^"]*"|'[^']*'/, "string"],
      [/\|/, "delimiter"],
      [/\d+(\.\d+)?/, "number"],
      [/(?:true|false|nil|null|blank|empty)\b/, "keyword"],
      [/[a-zA-Z_][\w.]*/, "variable"],
      [/./, "variable"],
    ],
    liquidTag: [
      [/-?%\}/, { token: "delimiter.expression", next: "@pop" }],
      [/"[^"]*"|'[^']*'/, "string"],
      [/[=!<>]=?|!=/, "operator"],
      [/\d+(\.\d+)?/, "number"],
      [/(?:if|elsif|else|endif|unless|endunless|for|endfor|case|when|endcase|assign|capture|endcapture|comment|endcomment|include|render|raw|endraw|tablerow|endtablerow|break|continue|cycle|increment|decrement)\b/, "keyword"],
      [/(?:true|false|nil|null|blank|empty)\b/, "keyword"],
      [/(?:and|or|not|contains|in)\b/, "keyword"],
      [/[a-zA-Z_]\w*/, "variable"],
      [/./, "variable"],
    ],
    htmlTag: [
      [/\/?>/, { token: "delimiter.html", next: "@pop" }],
      [/\{\{-?/, { token: "delimiter.expression", next: "@liquidOutput" }],
      [/\{%-?/, { token: "delimiter.expression", next: "@liquidTag" }],
      [/[a-zA-Z][\w-]*(?=\s*=)/, "attribute.name"],
      [/=/, "delimiter"],
      [/"[^"]*"|'[^']*'/, "attribute.value"],
      [/[a-zA-Z][\w-]*/, "tag"],
      [/\s+/, ""],
    ],
    htmlComment: [
      [/--!?>/, { token: "comment", next: "@pop" }],
      [/./, "comment"],
    ],
  },
};

export const languageConfiguration: languages.LanguageConfiguration = {
  comments: { blockComment: ["<!--", "-->"] },
  brackets: [["<", ">"], ["{", "}"], ["(", ")"], ["[", "]"]],
  autoClosingPairs: [
    { open: "{", close: "}" }, { open: "[", close: "]" },
    { open: "(", close: ")" }, { open: '"', close: '"' },
    { open: "'", close: "'" }, { open: "<!--", close: "-->" },
  ],
  surroundingPairs: [
    { open: '"', close: '"' }, { open: "'", close: "'" }, { open: "<", close: ">" },
  ],
};

export const snippetCompletions = [
  { label: "<extends>", detail: "Maizzle layout extends",
    insertText: '<extends src="${1:src/layouts/main.html}">\n\t$0\n</extends>' },
  { label: "<block>", detail: "Maizzle content block",
    insertText: '<block name="${1:content}">\n\t$0\n</block>' },
  { label: "<component>", detail: "Maizzle component include",
    insertText: '<component src="${1:src/components/}">\n\t$0\n</component>' },
  { label: "{{ }}", detail: "Liquid output tag", insertText: "{{ ${1:variable} }}" },
  { label: "{% if %}", detail: "Liquid if block",
    insertText: '{% if ${1:condition} %}\n\t$0\n{% endif %}' },
  { label: "{% for %}", detail: "Liquid for loop",
    insertText: '{% for ${1:item} in ${2:collection} %}\n\t$0\n{% endfor %}' },
  { label: "<!--[if mso]>", detail: "MSO conditional for Outlook",
    insertText: "<!--[if mso]>\n$0\n<![endif]-->" },
];
