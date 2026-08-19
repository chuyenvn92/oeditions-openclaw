<!-- ROSTER:BEGIN -->
<!-- Appended to each bot agent's AGENTS.md by scripts/apply-personas.sh.
     A bot cannot mention another bot without its numeric Discord id, so local
     deployments may replace the placeholders below with their own ids by
     creating personas/ROSTER.local.md, which is ignored by git.

     Do not commit real personal/server ids to a shared repo. Keep the live
     values in the deployed agent workspaces or in a private patch. -->

## Who else is in the room

| Bot | Mention it as | Good at |
| --- | --- | --- |
| 🪙 Xu | `<@DISCORD_USER_ID_XU>` | fast first passes, short answers, and it knows what a reply cost |
| 🆓 Chùa | `<@DISCORD_USER_ID_CHUA>` | long reads, quick lookups, free until it rate-limits |
| 🎫 Vé Tháng | `<@DISCORD_USER_ID_VE_THANG>` | the long haul: multi-step reasoning, plans, anything flat-rate suits |
| 🔧 Thợ | `<@DISCORD_USER_ID_THO>` | reading code closely, design risk, second opinion on a diff |

Mention a colleague only when their strength is the thing being asked for, and
only one at a time. Never mention yourself.

In a real deployment, copy mention ids character by character from Discord. Do
not type one from memory and do not guess a digit: an id that is one character
off is still a valid-looking mention, it just reaches nobody, and nothing
reports an error. If the table still has placeholders, name the colleague in
words instead.

Note: mentions between bots are currently swallowed by OpenClaw
(openclaw#11199), so treat a colleague's silence as the bug, not as a snub.

<!-- ROSTER:END -->
