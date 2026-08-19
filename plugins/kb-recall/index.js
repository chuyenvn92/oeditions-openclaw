import { readFile } from "node:fs/promises";
import { homedir } from "node:os";
import path from "node:path";

const DEFAULT_CONFIG = {
  agents: ["deepseek"],
  allowedChatTypes: ["direct", "group", "channel", "unknown"],
  indexPath: path.join(homedir(), "data", "knowledge-index.json"),
  maxResults: 3,
  minScore: 0.3,
  maxSnippetChars: 500,
  triggers: {
    minChars: 8,
    // Room convention is Vietnamese-by-default — the plugin this replaces
    // (qmd-recall) shipped an English-only trigger list and silently never
    // fired for messages here. Kept short on purpose; extend via config
    // rather than growing this default list.
    include: ["nho", "la gi", "the nao", "quyet dinh", "quy uoc", "kb-search", "notes"],
    exclude: ["ok", "yes", "no", "thanks", "lol"],
  },
};

function mergeConfig(raw) {
  const input = raw && typeof raw === "object" ? raw : {};
  return {
    ...DEFAULT_CONFIG,
    ...input,
    agents: Array.isArray(input.agents) ? input.agents : DEFAULT_CONFIG.agents,
    allowedChatTypes: Array.isArray(input.allowedChatTypes)
      ? input.allowedChatTypes
      : DEFAULT_CONFIG.allowedChatTypes,
    triggers: {
      ...DEFAULT_CONFIG.triggers,
      ...(input.triggers || {}),
      include: Array.isArray(input.triggers?.include)
        ? input.triggers.include
        : DEFAULT_CONFIG.triggers.include,
      exclude: Array.isArray(input.triggers?.exclude)
        ? input.triggers.exclude
        : DEFAULT_CONFIG.triggers.exclude,
    },
  };
}

function resolveAgentId(ctx) {
  if (ctx?.agentId?.trim()) return ctx.agentId.trim();
  const match = /^agent:([^:]+)/.exec(ctx?.sessionKey ?? "");
  return match?.[1] ?? "unknown";
}

function resolveChatType(ctx) {
  if (ctx?.chatType) return ctx.chatType;
  const key = ctx?.sessionKey ?? "";
  if (key.includes(":discord:channel:")) return "channel";
  if (key.includes(":discord:group:")) return "group";
  if (key.includes(":discord:")) return "direct";
  if (key.includes(":telegram:direct:")) return "direct";
  if (key.includes(":slack:") || key.includes(":telegram:group:")) return "group";
  return "unknown";
}

function isAllowedContext(config, ctx) {
  return (
    config.agents.includes(resolveAgentId(ctx)) &&
    config.allowedChatTypes.includes(resolveChatType(ctx))
  );
}

function buildQuery(event) {
  const latest = (event.prompt ?? "").trim();
  if (latest) return latest;
  const recent = (event.messages ?? [])
    .filter((m) => m.role === "user")
    .slice(-1)
    .map((m) => extractMessageText(m))
    .filter(Boolean)
    .join("\n");
  return recent;
}

function extractMessageText(message) {
  if (typeof message.text === "string") return message.text;
  if (typeof message.content === "string") return message.content;
  if (Array.isArray(message.content)) {
    return message.content
      .map((part) => (part && typeof part === "object" && "text" in part ? String(part.text ?? "") : ""))
      .filter(Boolean)
      .join("\n");
  }
  return "";
}

// Match without diacritics too — trigger words above are stored plain, and
// user messages come in with full Vietnamese diacritics normally, so strip
// tone marks from the message before comparing.
function stripDiacritics(text) {
  return text.normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/đ/g, "d").replace(/Đ/g, "D");
}

function shouldRecall(message, config) {
  const normalized = message.trim().replace(/\s+/g, " ");
  if (!normalized) return { shouldRun: false, reason: "empty" };
  const lower = stripDiacritics(normalized.toLowerCase());
  if (config.triggers.exclude.some((term) => lower === term.toLowerCase())) {
    return { shouldRun: false, reason: "excluded-exact" };
  }
  if (normalized.length < config.triggers.minChars) {
    return { shouldRun: false, reason: "too-short" };
  }
  const matched = config.triggers.include.find((term) => lower.includes(term.toLowerCase()));
  return matched ? { shouldRun: true, reason: `include:${matched}` } : { shouldRun: false, reason: "no-trigger" };
}

async function readSecretsEnv() {
  try {
    const text = await readFile(path.join(homedir(), ".openclaw", "secrets.env"), "utf8");
    const vars = {};
    for (const line of text.split("\n")) {
      const match = /^([A-Z_][A-Z0-9_]*)=['"]?([^'"]*)['"]?$/.exec(line.trim());
      if (match) vars[match[1]] = match[2];
    }
    return vars;
  } catch {
    return {};
  }
}

function cosine(a, b) {
  let dot = 0, na = 0, nb = 0;
  for (let i = 0; i < a.length; i++) {
    dot += a[i] * b[i];
    na += a[i] * a[i];
    nb += b[i] * b[i];
  }
  if (na === 0 || nb === 0) return 0;
  return dot / (Math.sqrt(na) * Math.sqrt(nb));
}

async function embedQuery(text, apiKey, timeoutMs) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch("https://api.cohere.com/v2/embed", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${apiKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        texts: [text],
        model: "embed-v4.0",
        input_type: "search_query",
        embedding_types: ["float"],
      }),
      signal: controller.signal,
    });
    if (!res.ok) {
      const body = await res.text();
      throw new Error(`cohere http ${res.status}: ${body.slice(0, 200)}`);
    }
    const data = await res.json();
    return data.embeddings.float[0];
  } finally {
    clearTimeout(timer);
  }
}

async function loadIndex(indexPath) {
  const text = await readFile(indexPath, "utf8");
  return JSON.parse(text);
}

function formatBlock(hits, config) {
  if (hits.length === 0) return null;
  const lines = [
    "Relevant notes from the user's own knowledge base:",
    ...hits.map((h) => `- [${h.file}] ${truncate(h.text.replace(/\s+/g, " ").trim(), config.maxSnippetChars)}`),
    "Use only if relevant. Do not mention this search unless asked.",
  ];
  return lines.join("\n");
}

function truncate(text, max) {
  if (text.length <= max) return text;
  return `${text.slice(0, Math.max(0, max - 1)).trimEnd()}…`;
}

export default {
  id: "kb-recall",
  name: "KB Recall",
  description: "Before-prompt recall over a Cohere-embedded local notes index.",
  register(api) {
    api.on("before_prompt_build", async (event, ctx) => {
      const config = mergeConfig(api.pluginConfig);

      if (!isAllowedContext(config, ctx)) {
        api.logger.debug?.(`kb-recall: skip context agent=${resolveAgentId(ctx)} chatType=${resolveChatType(ctx)}`);
        return;
      }

      const query = buildQuery(event);
      const decision = shouldRecall(query, config);
      if (!decision.shouldRun) {
        api.logger.debug?.(`kb-recall: skip reason=${decision.reason}`);
        return;
      }

      const startedAt = Date.now();
      try {
        const secrets = await readSecretsEnv();
        const apiKey = secrets.COHERE_API_KEY;
        if (!apiKey) {
          api.logger.warn?.("kb-recall: no COHERE_API_KEY in secrets.env, skipping");
          return;
        }

        const [queryVector, index] = await Promise.all([
          embedQuery(query, apiKey, 8000),
          loadIndex(config.indexPath),
        ]);

        const scored = index
          .map((entry) => ({ ...entry, score: cosine(queryVector, entry.vector) }))
          .filter((entry) => entry.score >= config.minScore)
          .sort((a, b) => b.score - a.score)
          .slice(0, config.maxResults);

        const block = formatBlock(scored, config);
        api.logger.info?.(
          `kb-recall: done status=${block ? "injected" : "empty"} elapsedMs=${Date.now() - startedAt} hits=${scored.length}`
        );
        if (!block) return;
        return { prependContext: block };
      } catch (error) {
        api.logger.warn?.(`kb-recall: error elapsedMs=${Date.now() - startedAt} ${error?.message ?? error}`);
      }
    });
  },
};
