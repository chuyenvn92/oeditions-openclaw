# OpenClaw Chief-of-Staff Kernel: Technical & Product Review

**Date:** 2026-08-20  
**Target Repository:** `oeditions-openclaw`  
**Review Scope:** Multi-agent workspace transformation from multi-bot chatroom into a private chief-of-staff kernel for side projects.  
**Reviewed Components:**
- Personas: [`personas/deepseek/SOUL.md`](file:///Users/chuyenkute/Downloads/oeditions-openclaw/personas/deepseek/SOUL.md), [`personas/codex/SOUL.md`](file:///Users/chuyenkute/Downloads/oeditions-openclaw/personas/codex/SOUL.md), [`personas/ROOM-RULES.md`](file:///Users/chuyenkute/Downloads/oeditions-openclaw/personas/ROOM-RULES.md), [`personas/ROSTER.md`](file:///Users/chuyenkute/Downloads/oeditions-openclaw/personas/ROSTER.md)
- Scripts: [`scripts/open-loops*`](file:///Users/chuyenkute/Downloads/oeditions-openclaw/scripts/open-loops.py), [`scripts/github-review*`](file:///Users/chuyenkute/Downloads/oeditions-openclaw/scripts/github-review.py), [`scripts/ask-agent*`](file:///Users/chuyenkute/Downloads/oeditions-openclaw/scripts/ask-agent.py), [`scripts/kb-save.py`](file:///Users/chuyenkute/Downloads/oeditions-openclaw/scripts/kb-save.py), [`scripts/safe-crawl.py`](file:///Users/chuyenkute/Downloads/oeditions-openclaw/scripts/safe-crawl.py), [`scripts/web-search.py`](file:///Users/chuyenkute/Downloads/oeditions-openclaw/scripts/web-search.py), [`scripts/schedule-reminder.py`](file:///Users/chuyenkute/Downloads/oeditions-openclaw/scripts/schedule-reminder.py)
- Documentation & Slides: [`docs/session-organization.md`](file:///Users/chuyenkute/Downloads/oeditions-openclaw/docs/session-organization.md), [`docs/xu-personal-assistant-status.md`](file:///Users/chuyenkute/Downloads/oeditions-openclaw/docs/xu-personal-assistant-status.md), [`docs/discord-setup.md`](file:///Users/chuyenkute/Downloads/oeditions-openclaw/docs/discord-setup.md), [`docs/runbook.md`](file:///Users/chuyenkute/Downloads/oeditions-openclaw/docs/runbook.md), [`docs/presentation.html`](file:///Users/chuyenkute/Downloads/oeditions-openclaw/docs/presentation.html)

---

## 1. Executive Summary

The transition from a 4-bot noisy Discord chatroom to a private **Chief-of-Staff Kernel** is architecturally sound:
- **Xu (DeepSeek API):** Front desk router, fast triage, low cost (~$0.001/turn), KB search/save, web search, GitHub review requests triage, open-loops tracking.
- **Vé Tháng (Codex CLI):** Deep work partner, flat-rate subscription, planning, multi-step code reasoning, and synthesis.
- **Chùa (Gemini) & Thợ (Qoder):** On-demand specialists, completely quiet unless directly human-tagged.
- **Privacy Model:** Strict isolation — no personal Gmail access; separation of identity; curated KB memory instead of raw personal inbox dumps.
- **Token Economics:** Channel = domain, thread = task session boundary, durable state stored in KB/open-loops rather than bloated message histories.

However, several runtime bugs, allowlist discrepancies, and tooling gaps prevent the system from operating as a fully autonomous chief-of-staff engine.

---

## 2. Findings: Mismatches, Overclaims & Discrepancies

### 2.1. Tool Path Formatting in `SOUL.md` vs Gateway Allowlist
- **Severity:** `HIGH`
- **Reference:** [`personas/deepseek/SOUL.md:L51-78`](file:///Users/chuyenkute/Downloads/oeditions-openclaw/personas/deepseek/SOUL.md#L51-L78) vs [`docs/xu-personal-assistant-status.md:L115-L117`](file:///Users/chuyenkute/Downloads/oeditions-openclaw/docs/xu-personal-assistant-status.md#L115-L117)
- **Problem:** `status.md` explicitly records that tilde paths (`~/oeditions/scripts/...`) fail on live OpenClaw gateway allowlist matching and must use absolute paths (`/home/openclaw/REDACTED-REPO-PATH/scripts/...`). Yet, `personas/deepseek/SOUL.md` still instructs Xu with `~/oeditions/scripts/...`.
- **Impact:** If Xu follows its persona instructions literally, exec calls risk instant rejection by the gateway allowlist.

### 2.2. Single-Direction Delegation vs Room Rules Claim
- **Severity:** `MEDIUM`
- **Reference:** [`scripts/ask-agent.py:L38-39`](file:///Users/chuyenkute/Downloads/oeditions-openclaw/scripts/ask-agent.py#L38-L39) vs [`personas/ROOM-RULES.md:L18-19`](file:///Users/chuyenkute/Downloads/oeditions-openclaw/personas/ROOM-RULES.md#L18-L19)
- **Problem:** `ROOM-RULES.md` states: *"Xu may consult Vé Tháng and Vé Tháng may consult Xu"*. But `ask-agent.py` hardcodes `ALLOWED_AGENT_IDS = {"codex"}`. Vé Tháng cannot consult Xu through this script. Furthermore, `ask-agent.py` docstrings advertise aliases for `qoder`, `gemini`, and `deepseek` which are rejected at runtime.
- **Impact:** Misleading docs; impossible for Codex to trigger a fast check from Xu via `ask-agent`.

### 2.3. `open-loops` Is Read-Only (Missing Mutation Primitive)
- **Severity:** `HIGH`
- **Reference:** [`scripts/open-loops.py`](file:///Users/chuyenkute/Downloads/oeditions-openclaw/scripts/open-loops.py) vs [`scripts/kb-save.py:L55-64`](file:///Users/chuyenkute/Downloads/oeditions-openclaw/scripts/kb-save.py#L55-L64)
- **Problem:** Xu is tasked with tracking side-project open loops, but `open-loops.py` only parses and prints `~/data/knowledge/open-loops.md`. There is no script to update project state. If Xu attempts to update it via `kb-save "<note>" --topic open-loops`, `kb-save.py` appends generic bullet entries (`- [YYYY-MM-DD] ...`), breaking the structured section parser in `open-loops.py`.
- **Impact:** The status board becomes stale unless updated by manual SSH file edits.

---

## 3. Security & Reliability Audit

### 3.1. Subprocess Execution Bug in `ask-agent.py`
- **Severity:** `CRITICAL`
- **Reference:** [`scripts/ask-agent.py:L50`](file:///Users/chuyenkute/Downloads/oeditions-openclaw/scripts/ask-agent.py#L50)
  ```python
  openclaw_bin = subprocess.run(["command", "-v", "openclaw"], capture_output=True, text=True, shell=True).stdout.strip()
  ```
- **Vulnerability / Bug:** When `shell=True` is used with an argument list in Python `subprocess.run`, `/bin/sh` executes only the first element (`command`), ignoring `-v` and `openclaw`. `openclaw_bin` returns empty string.
- **Consequence:** The script falls back to hardcoded paths ([`ask-agent.py:L55-62`](file:///Users/chuyenkute/Downloads/oeditions-openclaw/scripts/ask-agent.py#L55-L62)) containing macOS `/opt/homebrew/bin/openclaw` and a specific node version `~/.nvm/versions/node/v22.22.3/...`. On a Linux VPS with a different node path, `ask-agent` fails with `FileNotFoundError`.

### 3.2. Statelessness & Session Context Drift in Agent Delegation
- **Severity:** `MEDIUM`
- **Reference:** [`scripts/ask-agent.py:L89-93`](file:///Users/chuyenkute/Downloads/oeditions-openclaw/scripts/ask-agent.py#L89-L93)
- **Problem:** The CLI invocation `openclaw agent --agent codex --message <prompt>` does not pass a `--session-key`. Each consult executes in an isolated or default session without context of the current Discord thread.
- **Consequence:** Codex cannot see prior decisions in that specific thread unless Xu's prompt includes the full 6-line Handoff Brief ([`docs/session-organization.md:L58-65`](file:///Users/chuyenkute/Downloads/oeditions-openclaw/docs/session-organization.md#L58-L65)).

### 3.3. Synchronous Embedding Re-index on Every Note Save
- **Severity:** `MEDIUM`
- **Reference:** [`scripts/kb-save.py:L68-78`](file:///Users/chuyenkute/Downloads/oeditions-openclaw/scripts/kb-save.py#L68-L78)
- **Problem:** Every `kb-save` call synchronously invokes `kb-index.py`, calling the Cohere API to re-embed all chunks across all knowledge files.
- **Consequence:** As the KB grows past 100 files, `kb-save` will exceed Gateway tool timeouts (30s) and hit Cohere rate limits, blocking Xu's response turn.

### 3.4. Codex CLI Backend Unsandboxed Access Boundary
- **Severity:** `MEDIUM` (Documented Trade-off)
- **Reference:** [`scripts/render-cli-backends.sh:L47`](file:///Users/chuyenkute/Downloads/oeditions-openclaw/scripts/render-cli-backends.sh#L47), [`docs/runbook.md:L46-56`](file:///Users/chuyenkute/Downloads/oeditions-openclaw/docs/runbook.md#L46-L56)
- **Context:** Codex runs with `--dangerously-bypass-approvals-and-sandbox` because bubblewrap fails on the GCP VM. `tools.deny` does not apply to CLI backends.
- **Guardrail:** The single defense layer is the Discord private guild & user allowlist. No unverified user or ambient trigger should be allowed to invoke Codex.

---

## 4. Architectural Assessment: `open-loops` as a Chief-of-Staff Primitive

| Dimension | Evaluation | Recommendation |
| :--- | :--- | :--- |
| **Format & Structure** | **Strong:** Pure Markdown schema (`## Project`, `- Status:`, `- Next:`, `- Channel:`, `- Updated:`) provides high compression and deterministic parsing. | Keep schema intact in `~/data/knowledge/open-loops.md`. |
| **Tooling Boundary** | **Deficient:** Read-only (`open-loops.py`), forcing human to manually edit markdown files. | Implement a dedicated `open-loops-set.py` tool. |
| **Workflow Integration** | **Partial:** Xu reads it on triage, but cannot close loops when tasks conclude in Discord threads. | Enable Xu to update `Next` actions directly via allowlisted tool upon task agreement. |

---

## 5. Top 5 Actionable Improvements (1-Week Scope)

1. **Fix Path Discrepancies & Subprocess Invocation (`ask-agent.py`, `SOUL.md`)**
   - In `ask-agent.py`, replace broken `subprocess.run(["command", "-v", "openclaw"], shell=True)` with `shutil.which("openclaw")` or standard PATH resolution.
   - Update `personas/deepseek/SOUL.md` to reference the exact absolute paths configured in OpenClaw gateway approvals (`/home/openclaw/REDACTED-REPO-PATH/scripts/...`).

2. **Build `open-loops-set` Mutation Script**
   - Create `scripts/open-loops-set.py` (and wrapper `scripts/open-loops-set`):
     - Syntax: `scripts/open-loops-set "<project>" --status "..." --next "..." [--channel "..."] [--owner "..."]`
     - Deterministically updates or appends the target `## Project` block while preserving markdown formatting.
   - Add `/home/openclaw/REDACTED-REPO-PATH/scripts/open-loops-set *` to Xu's gateway allowlist.

3. **Thread-Scoped Handoffs in `ask-agent.py`**
   - Allow passing `--session-key` or compute a hash based on Discord channel/thread ID so Vé Tháng maintains context within the active task without leaking into unrelated projects.
   - Enforce Xu's 6-line Handoff Brief structure on every delegation turn.

4. **Asynchronous / Debounced KB Indexing**
   - Remove synchronous `subprocess.run` of `kb-index.py` from `kb-save.py`.
   - Trigger `kb-index.py` via background process (`subprocess.Popen`) or periodic cron (e.g. every 30 mins) to prevent gateway timeouts.

5. **Clean Up Inactive Scripts & Align Persona Rosters**
   - Either wire up a delivery daemon for `scripts/schedule-reminder.py` or move it to an archived/experimental directory to avoid confusion with verified live capabilities.
   - Align `personas/ROSTER.md` and `personas/ROOM-RULES.md` to accurately state that `ask-agent` delegates strictly from Xu to Codex.

---

## 6. Presentation Narrative Upgrade Plan (`docs/presentation.html`)

To shift the presentation from generic philosophical statements to an evidence-driven technical showcase:

1. **Slide 01 & 03 (Cost-Aware Architecture):**
   - Include measured figures: DeepSeek triage (~$0.001/call, ~2.5s latency) vs Codex deep pass (flat rate, 20-55s latency). Show why Xu filters 80% of inbound chatter before summoning Codex.
2. **Slide 07 (Two-Tier Security Model):**
   - Clarify the difference between Tier 1 (Gateway Tool Allowlist for API bots like Xu) and Tier 2 (Host-level iptables + Private Guild User Gating for CLI bots like Codex). Explain why `tools.deny` cannot constrain CLI binaries.
3. **Slide 08 (Empirical Evidence & Failure Modes):**
   - Highlight the real-world bug where Xu attempted `github-review facebook/react#123 2>&1` and was rejected by exact allowlist matching. Explain how strict allowlists prevent prompt-injected shell chaining.
4. **Slide 10 (Live Chief-of-Staff Demo Flow):**
   - Replace generic Q&A with a 3-step kernel workflow:
     1. Triage: `@Xu check open loops for side projects`
     2. Delegation: `@Xu create handoff brief for Vé Tháng on PR review`
     3. Mutation: `@Xu update open-loops status for video-maker to 'Phase 2 in progress'`
5. **Slide 11 (Token & Context Economics):**
   - Present a concrete comparison: Long persistent chatroom (~40,000 tokens/turn, high noise) vs Thread-scoped session + 6-line Brief (~1,500 tokens/turn), achieving >90% token reduction.
