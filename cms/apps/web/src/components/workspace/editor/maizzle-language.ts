import {
  StreamLanguage,
  type StringStream,
  type StreamParser,
  LanguageSupport,
} from "@codemirror/language";
import {
  autocompletion,
  snippetCompletion,
  type CompletionContext,
  type CompletionResult,
} from "@codemirror/autocomplete";

// --- State types ---

type TokenState = {
  mode:
    | "root"
    | "yamlFrontMatter"
    | "maizzleExpression"
    | "liquidOutput"
    | "liquidTag"
    | "tag"
    | "comment";
  /** Track position for front matter detection (line start) */
  sol: boolean;
};

const MAIZZLE_TAGS = new Set([
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
]);

const LIQUID_KEYWORDS = new Set([
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
]);

const LIQUID_CONSTANTS = new Set([
  "true",
  "false",
  "nil",
  "null",
  "blank",
  "empty",
]);

const LIQUID_OPERATORS = new Set(["and", "or", "not", "contains", "in"]);

// --- Stream Parser ---

const maizzleParser: StreamParser<TokenState> = {
  name: "Email HTML",
  startState(): TokenState {
    return { mode: "root", sol: true };
  },

  token(stream: StringStream, state: TokenState): string | null {
    switch (state.mode) {
      case "root":
        return tokenRoot(stream, state);
      case "yamlFrontMatter":
        return tokenYamlFrontMatter(stream, state);
      case "maizzleExpression":
        return tokenMaizzleExpression(stream, state);
      case "liquidOutput":
        return tokenLiquidOutput(stream, state);
      case "liquidTag":
        return tokenLiquidTag(stream, state);
      case "tag":
        return tokenTag(stream, state);
      case "comment":
        return tokenComment(stream, state);
      default:
        stream.next();
        return null;
    }
  },
};

function tokenRoot(stream: StringStream, state: TokenState): string | null {
  // YAML front matter at start of line
  if (stream.sol() && stream.match(/^---\s*$/)) {
    state.mode = "yamlFrontMatter";
    return "meta";
  }

  // Maizzle expression {{{ }}}
  if (stream.match("{{{")) {
    state.mode = "maizzleExpression";
    return "processingInstruction";
  }

  // Liquid output {{ }}
  if (stream.match(/^\{\{-?/)) {
    state.mode = "liquidOutput";
    return "processingInstruction";
  }

  // Liquid tag {% %}
  if (stream.match(/^\{%-?/)) {
    state.mode = "liquidTag";
    return "processingInstruction";
  }

  // MSO conditional comments
  if (
    stream.match(
      /^<!--\[if\s+(?:mso|gte\s+mso|lte\s+mso|gt\s+mso|lt\s+mso).*?\]>/
    )
  ) {
    return "comment";
  }
  if (stream.match("<![endif]-->")) {
    return "comment";
  }

  // HTML comments
  if (stream.match("<!--")) {
    state.mode = "comment";
    return "comment";
  }

  // Opening/closing tags — check for Maizzle tags
  if (stream.match(/^<\/?/)) {
    const tagMatch = stream.match(/^[\w-]+/, false);
    if (tagMatch && typeof tagMatch !== "boolean" && MAIZZLE_TAGS.has(tagMatch[0])) {
      stream.match(/^[\w-]+/);
      state.mode = "tag";
      return "special(tagName)";
    }
    state.mode = "tag";
    return "angleBracket";
  }

  // HTML entities
  if (stream.match(/^&\w+;/)) {
    return "character";
  }

  // Consume text content
  if (stream.match(/^[^<{&]+/)) {
    return null;
  }

  stream.next();
  return null;
}

function tokenYamlFrontMatter(
  stream: StringStream,
  state: TokenState
): string | null {
  if (stream.sol() && stream.match(/^---\s*$/)) {
    state.mode = "root";
    return "meta";
  }
  stream.skipToEnd();
  return "meta";
}

function tokenMaizzleExpression(
  stream: StringStream,
  state: TokenState
): string | null {
  if (stream.match("}}}")) {
    state.mode = "root";
    return "processingInstruction";
  }
  if (stream.match(/"[^"]*"/) || stream.match(/'[^']*'/)) {
    return "special(string)";
  }
  if (stream.match("|")) {
    return "processingInstruction";
  }
  if (stream.match(/^[a-zA-Z_]\w*/)) {
    return "special(variableName)";
  }
  stream.next();
  return "special(variableName)";
}

function tokenLiquidOutput(
  stream: StringStream,
  state: TokenState
): string | null {
  if (stream.match(/^-?\}\}/)) {
    state.mode = "root";
    return "processingInstruction";
  }
  if (stream.match(/"[^"]*"/) || stream.match(/'[^']*'/)) {
    return "special(string)";
  }
  if (stream.match("|")) {
    return "processingInstruction";
  }
  if (stream.match(/^\d+(\.\d+)?/)) {
    return "special(number)";
  }
  if (stream.match(/^[a-zA-Z_][\w.]*/)) {
    const matched = stream.current();
    if (LIQUID_CONSTANTS.has(matched)) return "special(keyword)";
    return "special(variableName)";
  }
  stream.next();
  return "special(variableName)";
}

function tokenLiquidTag(
  stream: StringStream,
  state: TokenState
): string | null {
  if (stream.match(/^-?%\}/)) {
    state.mode = "root";
    return "processingInstruction";
  }
  if (stream.match(/"[^"]*"/) || stream.match(/'[^']*'/)) {
    return "special(string)";
  }
  if (stream.match(/^[=!<>]=?|^!=/)) {
    return "operator";
  }
  if (stream.match(/^\d+(\.\d+)?/)) {
    return "special(number)";
  }
  if (stream.match(/^[a-zA-Z_]\w*/)) {
    const matched = stream.current();
    if (LIQUID_KEYWORDS.has(matched)) return "special(keyword)";
    if (LIQUID_CONSTANTS.has(matched)) return "special(keyword)";
    if (LIQUID_OPERATORS.has(matched)) return "special(keyword)";
    return "special(variableName)";
  }
  stream.next();
  return "special(variableName)";
}

function tokenTag(stream: StringStream, state: TokenState): string | null {
  if (stream.match(/^\/?>/) ) {
    state.mode = "root";
    return "angleBracket";
  }
  // Liquid inside attributes
  if (stream.match(/^\{\{-?/)) {
    state.mode = "liquidOutput";
    return "processingInstruction";
  }
  if (stream.match(/^\{%-?/)) {
    state.mode = "liquidTag";
    return "processingInstruction";
  }
  // Tag name (first word after <)
  if (stream.match(/^[a-zA-Z][\w-]*/)) {
    return "tagName";
  }
  if (stream.match("=")) {
    return "angleBracket";
  }
  if (stream.match(/"[^"]*"/) || stream.match(/'[^']*'/)) {
    return "attributeValue";
  }
  if (stream.match(/^[a-zA-Z_][\w-]*/)) {
    return "attributeName";
  }
  if (stream.eatSpace()) {
    return null;
  }
  stream.next();
  return null;
}

function tokenComment(
  stream: StringStream,
  state: TokenState
): string | null {
  if (stream.match("-->")) {
    state.mode = "root";
    return "comment";
  }
  stream.match(/^(?:(?!-->).)+/) || stream.next();
  return "comment";
}

// --- Completions ---

const maizzleCompletions = [
  snippetCompletion(
    '<extends src="${src/layouts/main.html}">\n\t${}\n</extends>',
    {
      label: "<extends>",
      detail: "Maizzle layout extends",
      type: "keyword",
    }
  ),
  snippetCompletion('<block name="${content}">\n\t${}\n</block>', {
    label: "<block>",
    detail: "Maizzle content block",
    type: "keyword",
  }),
  snippetCompletion(
    '<component src="${src/components/}">\n\t${}\n</component>',
    {
      label: "<component>",
      detail: "Maizzle component include",
      type: "keyword",
    }
  ),
  snippetCompletion("{{ ${variable} }}", {
    label: "{{ }}",
    detail: "Liquid output tag",
    type: "keyword",
  }),
  snippetCompletion("{% if ${condition} %}\n\t${}\n{% endif %}", {
    label: "{% if %}",
    detail: "Liquid if block",
    type: "keyword",
  }),
  snippetCompletion(
    "{% for ${item} in ${collection} %}\n\t${}\n{% endfor %}",
    {
      label: "{% for %}",
      detail: "Liquid for loop",
      type: "keyword",
    }
  ),
  snippetCompletion("<!--[if mso]>\n${}\n<![endif]-->", {
    label: "<!--[if mso]>",
    detail: "MSO conditional comment for Outlook",
    type: "keyword",
  }),
];

function maizzleCompletionSource(
  context: CompletionContext
): CompletionResult | null {
  const word = context.matchBefore(/[\w<{!-]*/);
  if (!word || (word.from === word.to && !context.explicit)) return null;
  return {
    from: word.from,
    options: maizzleCompletions,
  };
}

// --- Export ---

export function maizzleLanguage(): LanguageSupport {
  const lang = StreamLanguage.define(maizzleParser);
  return new LanguageSupport(lang, [
    autocompletion({ override: [maizzleCompletionSource] }),
  ]);
}
