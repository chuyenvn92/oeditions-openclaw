# oeditions-openclaw

> **Một Discord server riêng biến thành không gian làm việc đa AI (Multi-AI Workspace)**\
> Mỗi mô hình AI đóng vai một thành viên chuyên trách trong phòng chat: tag tên ai, người đó trả lời.

---

## 👥 Biệt Đội 4 Bot Trong Phòng

| Bot | Tên Agent | Mô hình & Loại kết nối | Chi phí / Cơ chế | Vai trò chính |
| :--- | :--- | :--- | :--- | :--- |
| **🪙 Xu** | `deepseek` | DeepSeek API (`deepseek/deepseek-chat`) | Theo API key | Đọc nhanh lượt đầu, tóm tắt, báo giá |
| **🆓 Chùa** | `gemini` | Google Gemini (`gemini-2.5-flash`) | Miễn phí (5 req/phút) | Đọc văn bản siêu dài, tra cứu nhanh |
| **🔧 Thợ** | `qoder` | Qoder CLI (`qoder-cli/auto`) | Dùng token cá nhân | Soi code, rà soát diff, tìm rủi ro logic |
| **🎫 Vé Tháng** | `codex` | Codex CLI (`codex-cli/gpt-5.4`) | Trọn gói ChatGPT Plus | Suy luận dài, lập kế hoạch phức tạp |

> Còn một persona thứ 5, **`claude`** (`personas/claude/`), dùng làm reviewer nội bộ — không gắn bot Discord riêng, các bot khác tham vấn nó qua agent-to-agent thay vì tag trong kênh. Không nằm trong 4 bước cài đặt nhanh dưới đây; muốn dùng thì tự `openclaw agents add claude ...` rồi chạy lại `scripts/apply-personas.sh`.

---

## 💻 Yêu cầu hệ thống (Prerequisites)

Dự án hỗ trợ **tất cả hệ điều hành**:

* **macOS**: Mở ứng dụng **Terminal** có sẵn.
* **Linux / VPS (Ubuntu 22.04/24.04)**: Dùng shell SSH hoặc Terminal.
* **Windows**: Sử dụng **WSL2 (Ubuntu)** để đảm bảo các script bash và sandbox hoạt động hoàn hảo:
  ```powershell
  # Mở PowerShell (Run as Administrator) trên Windows và gõ:
  wsl --install -d Ubuntu
  # Sau khi khởi động lại máy, mở ứng dụng "Ubuntu" vừa cài để thao tác.
  ```

### Cài đặt Node.js (Yêu cầu Node >= 22.22.3)
Chạy lệnh sau trong Terminal (macOS / Linux / WSL2):
```bash
# Kiểm tra phiên bản Node hiện tại
node -v

# Nếu chưa có hoặc Node cũ (< 22.22.3), cài nhanh qua nvm:
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash
export NVM_DIR="$HOME/.nvm" && [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
nvm install 22.22.3
nvm use 22.22.3
```

---

## 🚀 Hướng Dẫn Cài Đặt Từng Bước (Quickstart)

### Bước 1: Tạo Bot Discord & Lấy Token (Làm 4 lần cho 4 bot)

1. Truy cập [Discord Developer Portal](https://discord.com/developers/applications).
2. Nhấn **New Application** → Đặt tên bot (Ví dụ: `Xu`, `Chùa`, `Thợ`, `Vé Tháng`).
3. Vào tab **Bot**:
   * Nhấn **Reset Token** → Sao chép mã Token lưu vào máy.
   * Kéo xuống mục **Privileged Gateway Intents** → Bật **Message Content Intent** (Bắt buộc để bot đọc được tin nhắn).
4. Vào tab **OAuth2** → **URL Generator**:
   * Mục *Scopes*: Tích chọn `bot` và `applications.commands`.
   * Mục *Bot Permissions*: Tích chọn `View Channels`, `Send Messages`, `Read Message History`.
   * Sao chép link ở dưới cùng → Dán vào trình duyệt để mời bot vào Discord server riêng của bạn.

---

### Bước 2: Cài Đặt OpenClaw & Cấu Hình Môi Trường

Chạy các lệnh sau trong Terminal:

```bash
# 1. Cài đặt OpenClaw CLI
npm install -g openclaw@latest

# 2. Khởi tạo cấu hình gateway
openclaw onboard --non-interactive --accept-risk \
  --mode local --auth-choice skip \
  --gateway-port 18789 --gateway-bind loopback \
  --install-daemon --daemon-runtime node \
  --skip-channels --skip-skills --skip-search --skip-hooks --skip-ui

# 3. Cài đặt plugin Discord + provider DeepSeek + plugin KB Recall
openclaw plugins install @openclaw/discord
openclaw plugins install clawhub:@openclaw/deepseek-provider
openclaw plugins install ./plugins/kb-recall

# 4. Cấu hình API keys cho các công cụ của Xu & Thợ (nếu dùng)
cat << 'EOF' > ~/.openclaw/secrets.env
COHERE_API_KEY="your-cohere-key"          # Cho kb-recall / kb-search (Semantic Search)
BROWSER_USE_API_KEY="your-browser-key"    # Cho browser-use (Cloud Browser Automation)
GITHUB_TOKEN="your-github-token"          # Cho github-review
QODER_PERSONAL_ACCESS_TOKEN="your-token"  # Cho Thợ (Qoder CLI)
EOF
chmod 600 ~/.openclaw/secrets.env

# 5. Clone dự án này về máy (nếu chưa clone)
git clone <your-fork-or-repo-url>
cd oeditions-openclaw

# 6. Tạo đường dẫn backend phù hợp với máy của bạn và áp dụng patch
scripts/render-cli-backends.sh
openclaw config patch --file config/cli-backends.generated.patch.json5
openclaw config patch --file config/qoder-replaces-pplx.patch.json5
openclaw config patch --file config/discord.patch.json5
openclaw config patch --file config/heartbeat-off.patch.json5

# 7. Tạo 4 agent trước khi bind Discord account vào chúng
openclaw agents add deepseek --non-interactive \
  --workspace "$HOME/.openclaw/workspaces/deepseek" \
  --model deepseek/deepseek-chat
openclaw agents add gemini --non-interactive \
  --workspace "$HOME/.openclaw/workspaces/gemini" \
  --model google/gemini-2.5-flash
openclaw agents add qoder --non-interactive \
  --workspace "$HOME/.openclaw/workspaces/qoder" \
  --model qoder-cli/auto
openclaw agents add codex --non-interactive \
  --workspace "$HOME/.openclaw/workspaces/codex" \
  --model codex-cli/gpt-5.4
```

---

### Bước 3: Gắn Token Discord Vào Từng Bot

Lưu các token bot đã lấy ở Bước 1 vào các file tạm rồi chạy script:

```bash
# Lưu token vào file tạm (thay YOUR_TOKEN bằng token thật)
echo "YOUR_DISCORD_TOKEN_XU" > ~/discord-xu.token
echo "YOUR_DISCORD_TOKEN_CHUA" > ~/discord-chua.token
echo "YOUR_DISCORD_TOKEN_THOI" > ~/discord-thoi.token
echo "YOUR_DISCORD_TOKEN_VE_THANG" > ~/discord-ve-thang.token

# Gắn bot vào OpenClaw
scripts/add-bot.sh deepseek xu-bot       ~/discord-xu.token
scripts/add-bot.sh gemini   chua-bot     ~/discord-chua.token
scripts/add-bot.sh qoder    thoi-bot     ~/discord-thoi.token
scripts/add-bot.sh codex    ve-thang-bot ~/discord-ve-thang.token

# Xoá file token tạm để bảo mật
rm ~/discord-*.token
```

---

### Bước 4: Áp Dụng Persona (Tính Cách & Luật Phòng)

```bash
# Đẩy toàn bộ tính cách và ID bot vào workspace của OpenClaw
scripts/apply-personas.sh

# Khởi động lại gateway để áp dụng toàn bộ cài đặt
openclaw daemon restart
```

---

### Bước 5: Thử Nghiệm Trên Discord

Vào Discord server của bạn và tag tên bot để bắt đầu:
* `@Xu giá Bitcoin hôm nay thế nào?`
* `@Chùa tóm tắt bài viết này giúp tôi: [link hoặc văn bản dài]`
* `@Thợ review đoạn code này xem có lỗi bảo mật nào không:`
* `@Vé Tháng lên kế hoạch phát triển dự án này trong 3 tháng:`

---

## 📂 Cấu Trúc Thư Mục (Layout)

```
config/*.json5            Cấu hình patch cho OpenClaw (backends, discord, heartbeat)
personas/                 Tính cách (IDENTITY), phong cách trả lời (SOUL) & luật phòng
personas/ROOM-RULES.md    Quy tắc chung mọi bot đều tuân theo
personas/ROSTER.md        Bảng danh sách và Discord ID của 4 bot
scripts/add-bot.sh        Gắn bot Discord vào agent OpenClaw
scripts/apply-personas.sh Đẩy persona vào gateway
scripts/qoder-cli.sh      Wrapper nạp token trước khi gọi Qoder CLI
scripts/render-cli-backends.sh Tự động dò tìm đường dẫn binary trên máy
docs/runbook.md           Hướng dẫn vận hành production trên VPS
docs/discord-setup.md     Chi tiết kiến trúc Multi-bot Discord
docs/vps-setup.md         Hướng dẫn chuyển từ máy local lên VPS
docs/upgrade-plan-agent-stack.md Kế hoạch nâng cấp Full-Stack AI Agent (Exa, QMD, Crawl4AI, ByteRover, Browser Use)
```

---

## ❓ Xử Lý Sự Cố Thường Gặp (Troubleshooting)

1. **Bot online trong server nhưng tag không thấy trả lời?**
   * *Nguyên nhân*: Chưa bật **Message Content Intent** trong Discord Developer Portal (Bước 1.3). Bật lên và khởi động lại gateway: `openclaw daemon restart`.
2. **Trên Windows báo lỗi không chạy được file `.sh`?**
   * *Khắc phục*: Hãy chắc chắn bạn đang chạy trong môi trường **WSL2 (Ubuntu)** chứ không phải Command Prompt hay PowerShell.
3. **Lỗi `Node version unsupported`?**
   * *Khắc phục*: Đảm bảo phiên bản Node `>= 22.22.3`. Kiểm tra bằng `node -v` và sử dụng `nvm use 22.22.3`.
4. **Lỗi `qoder not found` hoặc Qoder báo chưa login?**
   * *Khắc phục*: Cài Qoder CLI, đặt `QODER_PERSONAL_ACCESS_TOKEN` trong `.env` hoặc `~/.openclaw/secrets.env`, rồi thử `scripts/qoder-cli.sh status`.
