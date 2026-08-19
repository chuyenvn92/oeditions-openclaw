# 🚀 Kế Hoạch Nâng Cấp Toàn Diện Hệ Thống OpenClaw: Từ Multi-Bot Chat Đến Personal Assistant Đa Năng

> **Tài liệu thiết kế kiến trúc & Kế hoạch triển khai (Upgrade Implementation Plan)**  
> **Dự án:** `oeditions-openclaw`  
> **Mục tiêu:** Chuyển đổi phòng chat 4-Bot Discord hiện tại từ mô hình hỏi - đáp bị động (Pull-only) thành **Hệ sinh thái Trợ lý Cá nhân Chủ động (Proactive Personal Assistant)**: lấy **`🪙 Xu` (DeepSeek)** làm hạt nhân điều phối chính (tránh nghẽn rate-limit 5 req/phút của Gemini Free Tier), tự động đẩy tin định kỳ (Digest, cảnh báo, nhắc việc), ghi nhớ thói quen & sở thích người dùng (memory built-in của OpenClaw), tra cứu tri thức cục bộ (QMD), cào dữ liệu web an toàn (Exa + Crawl4AI với rào chắn SSRF ngay từ đầu), và tự động hóa trình duyệt (Browser Use) tuân thủ ranh giới bảo mật backend.

---

## 📑 Mục Lục
1. [Tổng Quan, Đánh Giá Hiện Trạng & Đánh Đổi Kiến Trúc](#1-tổng-quan-đánh-giá-hiện-trạng--đánh-đổi-kiến-trúc)
2. [Kiến Trúc Mục Tiêu: Cơ Chế Đẩy Chủ Động (Push) & Phản Hồi (Pull)](#2-kiến-trúc-mục-tiêu-cơ-chế-đẩy-chủ-động-push--phản-hồi-pull)
3. [Phân Bổ Tool Vào Từng Bot Theo Nguyên Tắc Chi Phí & Rủi Ro Backend](#3-phân-bổ-tool-vào-từng-bot-theo-nguyên-tắc-chi-phí--rủi-ro-backend)
4. [Lộ Trình Triển Khai 5 Giai Đoạn Cốt Lõi](#4-lộ-trình-triển-khai-5-giai-đoạn-cốt-lõi)
   - [Giai đoạn 1: Thiết lập Tầng Đẩy Tin Chủ Động & Cập Nhật Persona Cốt Lõi Cho Xu](#giai-đoạn-1-thiết-lập-tầng-đẩy-tin-chủ-động--cập-nhật-persona-cốt-lõi-cho-xu)
   - [Giai đoạn 2: Tích hợp Exa Search & Crawl4AI Đi Liền Rào Chắn SSRF Ngay Lập Tức](#giai-đoạn-2-tích-hợp-exa-search--crawl4ai-đi-liền-rào-chắn-ssrf-ngay-lập-tức)
   - [Giai đoạn 3: Triển khai Local RAG (QMD) & Bộ Nhớ Cá Nhân (OpenClaw memory built-in)](#giai-đoạn-3-triển-khai-local-rag-qmd--bộ-nhớ-cá-nhân-openclaw-memory-built-in)
   - [Giai đoạn 4: Tự Động Hóa Trình Duyệt (Browser Use) & Quản Trị Rủi Ro Backend](#giai-đoạn-4-tự-động-hóa-trình-duyệt-browser-use--quản-trị-rủi-ro-backend)
   - [Giai đoạn 5: Vận Hành Sản Xuất, Pairing Device & Giám Sát Chi Phí Token](#giai-đoạn-5-vận-hành-sản-xuất-pairing-device--giám-sát-chi-phí-token)
   - [Phụ lục Tùy Chọn: Tích hợp Model Provider Minimax (Optional)](#phụ-lục-tùy-chọn-tích-hợp-model-provider-minimax-optional)
5. [Cấu Trúc Files & Config Cần Bổ Sung Vào Dự Án](#5-cấu-trúc-files--config-cần-bổ-sung-vào-dự-án)
6. [Kịch Bản Kiểm Thử Toàn Trình (End-to-End Test Cases)](#6-kịch-bản-kiểm-thử-toàn-trình-end-to-end-test-cases)
7. [Dự Toán Tài Nguyên & Chi Phí Vận Hành](#7-dự-toán-tài-nguyên--chi-phí-vận-hành)

---

## 1. Tổng Quan, Đánh Giá Hiện Trạng & Đánh Đổi Kiến Trúc

### 1.1. Hiện trạng dự án `oeditions-openclaw`
* Đang chạy mô hình **Multi-AI Discord Workspace** với 4 bot: `🪙 Xu` (DeepSeek API), `🆓 Chùa` (Gemini API), `🔧 Thợ` (Qoder CLI), `🎫 Vé Tháng` (Codex CLI).
* **Điểm nghẽn lớn nhất:** Hệ thống thuần túy là **Pull** (người dùng phải tag tên thì bot mới trả lời). Thiếu hoàn toàn cơ chế **Push** chủ động (tự tổng hợp tin tức buổi sáng, theo dõi cảnh báo, nhắc nhở lịch trình cá nhân).
* **Rủi ro kỹ thuật đã ghi nhận (trong `docs/discord-setup.md`):**
  - `tools.deny` chỉ có hiệu lực với API backends (`Xu`, `Chùa`), nhưng **hoàn toàn vô hiệu (cosmetic)** với CLI backends (`Thợ`, `Vé Tháng`) vì các CLI này mang theo công cụ riêng và chạy với toàn quyền của user trên host.
  - Docker sandbox hiện đang tắt do lỗi fail-open (báo sandboxed nhưng thực tế chạy trực tiếp trên host).

### 1.2. Quyết định chuyển giao vai trò Personal Assistant từ `Chùa` sang `Xu`
* **Lý do chuyển đổi:** `🆓 Chùa` (Gemini) dùng gói Free Tier bị giới hạn cứng **5 requests/phút (5 RPM)**. Khi gộp toàn bộ các tác vụ: Push lịch trình định kỳ + Tìm kiếm Exa + Cào web Crawl4AI + Tra cứu QMD + Ghi memory + Browser Use, `Chùa` sẽ lập tức chạm trần rate limit đúng những lúc cần phản hồi gấp.
* **Lựa chọn `🪙 Xu` (DeepSeek API) làm Hạt nhân Trợ lý:** 
  - Chạy API trả phí theo token cực rẻ, không bị bóp nghẽn 5 RPM.
  - API backend hỗ trợ `tools.deny` thực sự ở tầng Gateway, kiểm soát an toàn khi kích hoạt Browser Use và web scraping.
* **Đánh đổi kiến trúc đã biết trước (Known Trade-off):** 
  - `🆓 Chùa` (Gemini) có ưu thế context khổng lồ (1M+ tokens), trong khi `🪙 Xu` (DeepSeek) có context tiêu chuẩn (64K - 128K tokens). 
  - *Giải pháp khắc phục:* Với các bài cào web quá dài từ Crawl4AI, hệ thống sẽ thực hiện chunking và tóm tắt theo đợt trước khi nạp vào context của Xu, hoặc khi cần đọc tài liệu thô nguyên khối cực lớn thì mới ủy quyền (delegate) một lần sang `Chùa`.

---

## 2. Kiến Trúc Mục Tiêu: Cơ Chế Đẩy Chủ Động (Push) & Phản Hồi (Pull)

```
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│                                   LUỒNG 1: PUSH CHỦ ĐỘNG                                 │
│                                                                                          │
│  ┌──────────────────────┐      ┌─────────────────────┐      ┌─────────────────────────┐  │
│  │ OpenClaw Scheduler   │ ───► │   🪙 Xu (DeepSeek)  │ ───► │ Discord Channel         │  │
│  │ (Cron: 07:30, 21:30) │      │ (Fetch Exa/QMD/Mem) │      │ "[PROACTIVE_DIGEST]..." │  │
│  └──────────────────────┘      └─────────────────────┘      └────────────┬────────────┘  │
│                                                                          │               │
│                                (Luật phòng: Chùa, Thợ, Vé Tháng IM LẶNG)  ▼               │
│                                                                 ┌─────────────────┐      │
│                                                                 │ Human Reads     │      │
│                                                                 └─────────────────┘      │
└──────────────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────────────────┐
│                                   LUỒNG 2: PULL THEO YÊU CẦU                             │
│                                                                                          │
│  Human Tag: "@Xu / @Chùa / @Thợ / @Vé Tháng"                                             │
│                        │                                                                 │
│                        ▼                                                                 │
│  ┌────────────────────────────────────────────────────────────────────────────────────┐  │
│  │ Gateway Router (Group Mention Gating + Loop Protection 20 events/60s)              │  │
│  └─────────────────────┬──────────────────────────────────────────────────────────────┘  │
│                        │                                                                 │
│      ┌─────────────────┼─────────────────┬─────────────────┐                             │
│      ▼                 ▼                 ▼                 ▼                             │
│  ┌───────────┐   ┌───────────┐     ┌───────────┐     ┌───────────┐                       │
│  │ 🪙 Xu     │   │ 🆓 Chùa   │     │ 🔧 Thợ    │     │ 🎫 Vé     │                       │
│  │ (DeepSeek)│   │ (Gemini)  │     │ (Qoder)   │     │ (Codex)   │                       │
│  └─────┬─────┘   └─────┬─────┘     └─────┬─────┘     └─────┬─────┘                       │
│        │               │                 │                 │                             │
│        ▼               ▼                 ▼                 ▼                             │
│  [Personal Hub]  [Bulk Reading]    [Code Logic]      [Deep Reasoning]                    │
│  [Exa Search]    [1M+ Context]     [Local Diff]      [Long-term Plan]                    │
│  [Crawl4AI+SSRF] [Free Big Read]                                                         │
│  [QMD Local RAG]                                                                         │
│  [OpenClaw Memory]                                                                       │
│  [Browser Use]                                                                           │
└──────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Phân Bổ Tool Vào Từng Bot Theo Nguyên Tắc Chi Phí & Rủi Ro Backend

| Bot | Backend & Mô hình | Cơ chế Sandbox / `tools.deny` | Công cụ được gán | Lý do phân bổ & Phạm vi trách nhiệm |
| :--- | :--- | :--- | :--- | :--- |
| **🪙 Xu** | DeepSeek (`deepseek-chat`) via **API Backend** | **Chặn thật** (`tools.deny` hoạt động chuẩn ở tầng Gateway) | **1. Chủ động Push (Cron)**<br>**2. Exa Search**<br>**3. Crawl4AI (SSRF guarded)**<br>**4. QMD Local RAG**<br>**5. OpenClaw Memory (built-in)**<br>**6. Browser Use (Safe)** | **Trung tâm Personal Assistant**: Không bị bóp nghẽn 5 RPM, chi phí API cực rẻ, tốc độ phản hồi nhanh, hỗ trợ đầy đủ `tools.deny` an toàn khi chạy Browser Use và cào dữ liệu web. |
| **🆓 Chùa** | Google Gemini (`gemini-2.5-flash`) via **API Backend** | **Chặn thật** | **Bulk Reading (Context 1M+)** | Đọc các file log siêu dài, tài liệu PDF nguyên cuốn, sách nghiên cứu lớn mà Xu cần ủy quyền đọc hộ để tiết kiệm token và tránh tràn context. |
| **🔧 Thợ** | Qoder CLI (`qoder-cli/auto`) via **CLI Backend** | ⚠️ **KHÔNG CÓ SANDBOX** (`tools.deny` vô hiệu, toàn quyền host) | **Chỉ dùng CLI nội bộ:** Soi code, rà soát diff, kiểm tra logic file local | **Tuyệt đối KHÔNG giao Browser Use hay Fetch URL ngoài** để tránh nguy cơ bot bị prompt injection rồi tự ý chạy lệnh shell phá hoại hệ thống. |
| **🎫 Vé Tháng** | Codex CLI (`codex-cli/gpt-5.4`) via **CLI Backend** | ⚠️ **KHÔNG CÓ SANDBOX** (`tools.deny` vô hiệu, toàn quyền host) | **Multi-step Reasoning & Strategy Planning** | Lập kế hoạch dài hạn, cấu trúc lộ trình công việc cá nhân. Không giao tác vụ cào web thô. |

---

## 4. Lộ Trình Triển Khai 5 Giai Đoạn Cốt Lõi

### Giai đoạn 1: Thiết lập Tầng Đẩy Tin Chủ Động & Cập Nhật Persona Cốt Lõi Cho Xu

#### 1. Cấu hình OpenClaw Cron Scheduler
* Thiết lập lịch chạy định kỳ trong Gateway, **chỉ định `🪙 Xu` là bot thực thi**:
  - `07:30 AM`: **Morning Briefing** (Thời tiết, tin tức nổi bật theo sở thích, việc cần làm trong ngày, giá coin/thị trường theo dõi).
  - `12:30 PM`: **Market & Tech Flash** (Điểm tin nhanh trưa).
  - `21:30 PM`: **Daily Wrap-up & Memory Sync** (Tổng kết ngày, kích hoạt memory built-in lưu trữ thói quen/tiến độ công việc vào MEMORY.md).

#### 2. Cập nhật Persona Cốt Lõi Của Xu (`personas/deepseek/`)
* **Thực trạng Persona hiện tại:** File `IDENTITY.md` và `SOUL.md` định nghĩa Xu là *"blunt, short, allergic to filler — two sentences beats ten"* (chỉ trả lời 1-2 câu ngắn, chuyên báo giá và lướt nhanh). Vai trò Personal Assistant hub (viết bản tin digest, tổng hợp bài crawl, quản lý hồ sơ người dùng) mâu thuẫn hoàn toàn với persona cũ này.
* **Cập nhật Identity & Soul thật sự cho Xu:**
  - *Đối với câu hỏi chat thông thường:* Vẫn giữ phong cách dứt khoát, đi thẳng vào trọng tâm, không chào hỏi rườm rà.
  - *Đối với vai trò Chief Personal Assistant & Proactive Digest:* Xu đóng vai trò Quản gia điều hành (Executive Chief of Staff) — có khả năng cấu trúc bản tin mạch lạc, gạch đầu dòng rõ ràng, tổng hợp sâu sắc dữ liệu từ QMD/Crawl4AI và nhớ mọi thói quen của người dùng.
  - Cập nhật cả 2 file `personas/deepseek/IDENTITY.md` và `personas/deepseek/SOUL.md`.

#### 3. Sửa đổi Luật Phòng `personas/ROOM-RULES.md`
* Bổ sung quy tắc nhận diện tin nhắn chủ động để ngăn chặn loop tin nhắn giữa các bot:
  ```markdown
  ## Autonomous broadcasts and Proactive messages
  - Messages starting with `[PROACTIVE_DIGEST]`, `[DAILY_REMINDER]`, or `[PRICE_ALERT]` are automated system broadcasts dispatched by Xu.
  - ALL other bots (Chùa, Thợ, Vé Tháng) MUST treat these messages as pure context: DO NOT reply, DO NOT summarize them, and NEVER tag another bot to comment on them unless explicitly commanded by a human afterwards.
  ```

---

### Giai đoạn 2: Tích hợp Exa Search & Crawl4AI Đi Liền Rào Chắn SSRF Ngay Lập Tức
* **Nguyên tắc an toàn:** Không bao giờ triển khai công cụ fetch URL mà không có rào chắn mạng đi kèm trong cùng một thời điểm.
* **Các bước triển khai:**
  1. **Tích hợp Exa Search API:**
     - Đăng ký `EXA_API_KEY`, khai báo patch `config/exa.patch.json5`.
     - Gán quyền gọi Exa duy nhất cho `🪙 Xu` để tra cứu thông tin theo yêu cầu người dùng và chuẩn bị bản tin định kỳ.
  2. **Cài đặt Crawl4AI Engine:**
     - Khởi tạo môi trường Python: `scripts/setup-crawl4ai.sh`.
     - Cài đặt `crawl4ai` và Playwright runtime.
  3. **RÀO CHẮN BẢO MẬT SSRF (Triển khai đồng thời trong Giai đoạn 2):**
     - Xây dựng module kiểm tra URL trước khi nạp vào Crawl4AI hoặc Exa:
       - **Chặn tuyệt đối Endpoint Cloud Metadata:** `169.254.169.254` (ngăn đánh cắp Google Cloud/AWS/DigitalOcean Token).
       - **Chặn toàn bộ dải IP nội bộ RFC 1918:** `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `127.0.0.0/8`, `localhost`.
       - **Domain Whitelist / Safe Scheme:** Chỉ cho phép protocol `http://` và `https://`, từ chối `file://`, `gopher://`, `dict://`.
     - Script wrapper `scripts/safe-crawl.py` chịu trách nhiệm validate IP DNS resolution trước khi Playwright gửi request.

---

### Giai đoạn 3: Triển khai Local RAG (QMD) & Bộ Nhớ Cá Nhân (OpenClaw memory built-in)
* **Mục tiêu:** Xây dựng bộ nhớ hiểu sâu sắc về **Người Dùng (User Profile & Habits)** và tra cứu tài liệu cá nhân cục bộ giao cho `🪙 Xu`.
* **Các bước triển khai:**
  1. **Thiết lập QMD (Local Knowledge Retrieval):**
     - Cài đặt QMD, tạo kho dữ liệu tài liệu cá nhân: `data/knowledge/` (chứa ghi chú cá nhân, tài liệu nghiên cứu, sách đã crawl).
     - Cấu hình hybrid search (vector search + FTS) chạy hoàn toàn trên local/VPS để bảo vệ sự riêng tư.
     - `🪙 Xu` sử dụng tool này để tra cứu tài liệu khi người dùng hỏi hoặc tổng hợp thông tin.
  2. **Dùng memory built-in của OpenClaw thay vì ByteRover.** ByteRover bị chặn đăng ký tài khoản mới (`app.byterover.dev`), và phần lớn thế mạnh của nó (chia sẻ memory giữa nhiều tool/IDE khác nhau, team spaces nhiều người dùng) không áp dụng cho một trợ lý cá nhân trong một phòng Discord. OpenClaw đã có sẵn plugin `memory-core` (bundled, đang bật mặc định) và các tool `memory_search`/`memory_get` đã có trong tool list của Xu, không cần cài hay đăng ký gì thêm:
     - `USER.md` — sở thích, phong cách trả lời, cách xưng hô.
     - `MEMORY.md` — bộ nhớ dài hạn, quyết định/sự kiện bền vững.
     - `memory/YYYY-MM-DD.md` — ghi chú theo ngày, ngữ cảnh công việc đang làm.
     - `DREAMS.md` — bản tóm tắt "dreaming" (consolidation nền tự động), tương đương "Daily Knowledge Mining" mà ByteRover quảng cáo.
     - Không lưu: mật khẩu, API key, token, PII — áp dụng như một quy tắc trong persona, không phải cơ chế kỹ thuật riêng.
     - **Đánh đổi đã biết:** memory này nằm trên đĩa VPS, không đồng bộ cloud — nếu VPS mất, memory mất theo. Bù bằng `openclaw backup` chạy định kỳ backup `~/.openclaw/workspaces/` ra ngoài VPS, thay vì phụ thuộc dịch vụ ngoài.

---

### Giai đoạn 4: Tự Động Hóa Trình Duyệt (Browser Use) & Quản Trị Rủi Ro Backend
* **Đánh giá rủi ro nghiêm ngặt:** `Thợ` (Qoder) và `Vé Tháng` (Codex) chạy CLI backend không có sandbox thật. Nếu giao Browser Use cho CLI backend, một cú prompt injection có thể dẫn đến việc bot dùng quyền host để đánh cắp session cookie hoặc token.
* **Quyết định kiến trúc:**
  1. **Chỉ gán Browser Use cho `🪙 Xu` (API backend):** Gateway OpenClaw có quyền chặn/lọc các tool không mong muốn thông qua `tools.deny` thật sự đối với DeepSeek API.
  2. **Cấu hình Browser Use Cloud / Remote Browser:**
     - Thiết lập kết nối API qua `config/browser-use.patch.json5`.
     - Giới hạn tối đa **2 sessions đồng thời** (để giữ trong Free Tier 3 agents).
     - Thiết lập Hard Timeout: 90s cho mỗi phiên duyệt web.
  3. **Phạm vi sử dụng:** Đăng nhập vào các trang tin tức/diễn đàn có tài khoản cá nhân để lấy báo cáo, tải file PDF/hóa đơn tự động, hoặc render các web app SPA phức tạp mà Crawl4AI không đọc được.

---

### Giai đoạn 5: Vận Hành Sản Xuất, Pairing Device & Giám Sát Chi Phí Token
* **Mục tiêu:** Ổn định hệ thống trên môi trường VPS/Cloud và theo dõi chi phí DeepSeek.
* **Các bước triển khai:**
  1. **Xử lý Pair Device trên Cloud/VPS:**
     - Dashboard OpenClaw bind vào `127.0.0.1:18789`.
     - Sử dụng helper script `scripts/cloud-pair-tunnel.sh` để mở kết nối an toàn:
       ```bash
       ssh -N -L 18789:127.0.0.1:18789 user@VPS_IP
       ```
     - Truy cập `http://localhost:18789` trên máy local, vào mục Devices $\rightarrow$ bấm **Approve** xác thực thủ công.
  2. **Audit Logging & Giám sát chi phí DeepSeek:**
     - Ghi log toàn bộ các request push chủ động và các lần gọi tool vào `logs/assistant-audit.log`.
     - Theo dõi lượng token DeepSeek hàng ngày để cân đối ngân sách.

---

### Phụ lục Tùy Chọn: Tích hợp Model Provider Minimax (Optional)
* *Lưu ý:* Đây là tùy chọn mở rộng sau cùng, không nằm trong luồng Personal Assistant cốt lõi vì hệ thống đã có đủ 4 model chuyên biệt (`deepseek`, `gemini`, `qoder`, `codex`).
* Nếu cần một backend dự phòng với context window lớn và giá rẻ:
  - Cài đặt: `openclaw plugins install clawhub:@openclaw/minimax-provider`.
  - Cấu hình patch `config/minimax.patch.json5` làm model fallback cho `Xu` hoặc `Chùa` khi cần xử lý văn bản cực lớn.

---

## 5. Cấu Trúc Files & Config Cần Bổ Sung Vào Dự Án

```
oeditions-openclaw/
├── config/
│   ├── cli-backends.generated.patch.json5 # Cấu hình generated theo máy
│   ├── discord.patch.json5               # Cấu hình hiện tại
│   ├── heartbeat-off.patch.json5         # Cấu hình hiện tại
│   ├── cron-proactive.patch.json5        # [MỚI] Thiết lập lịch Cron Push tin cho Xu
│   ├── exa.patch.json5                   # [MỚI] Cấu hình Exa Search Provider gán cho Xu
│   ├── qmd.patch.json5                   # [MỚI] Cấu hình QMD Vector Engine
│   └── browser-use.patch.json5           # [MỚI] Cấu hình Browser Use gán riêng cho Xu
├── data/
│   └── knowledge/                        # [MỚI] Kho tài liệu cá nhân & bài cào sạch (QMD index)
# Hồ sơ người dùng (USER.md/MEMORY.md/memory/*.md) nằm sẵn trong
# ~/.openclaw/workspaces/deepseek/ — memory built-in của OpenClaw, không phải file trong repo này.
├── scripts/
│   ├── add-bot.sh                        # Script hiện tại
│   ├── apply-personas.sh                 # Script hiện tại (đã cập nhật luật Proactive & Persona Xu)
│   ├── render-cli-backends.sh            # Script hiện tại
│   ├── setup-crawl4ai.sh                 # [MỚI] Cài đặt Crawl4AI + Playwright
│   ├── safe-crawl.py                     # [MỚI] Python script cào web có chặn SSRF
│   ├── setup-qmd.sh                      # [MỚI] Khởi tạo QMD & local model embedding
│   ├── trigger-digest.sh                 # [MỚI] Trigger chạy thủ công hoặc test cron digest cho Xu
│   └── cloud-pair-tunnel.sh              # [MỚI] Helper SSH tunnel để pair dashboard an toàn
├── personas/
│   ├── ROOM-RULES.md                     # Cập nhật: Luật xử lý tin chủ động & phân quyền tool
│   ├── ROSTER.md                         # Cập nhật danh sách năng lực mới của 4 Bot
│   └── deepseek/                         # [CẬP NHẬT] Persona Xu: Thêm vai trò Chief Personal Assistant
└── docs/
    ├── upgrade-plan-agent-stack.md       # [TÀI LIỆU NÀY]
    ├── runbook.md                        # Runbook vận hành
    ├── discord-setup.md                  # Tài liệu kiến trúc Discord
    └── vps-setup.md                      # Hướng dẫn setup VPS
```

---

## 6. Kịch Bản Kiểm Thử Toàn Trình (End-to-End Test Cases)

| Mã kiểm thử | Tên kịch bản | Các bước thực hiện | Kết quả kỳ vọng |
| :--- | :--- | :--- | :--- |
| **TC-01** | *Proactive Morning Digest & Loop Safety* | Kích hoạt script `scripts/trigger-digest.sh` mô phỏng cron 7:30 AM | `🪙 Xu` tự động gửi bản tin `[PROACTIVE_DIGEST]` vào kênh. `Chùa`, `Thợ`, `Vé Tháng` hoàn toàn **im lặng**, không có hiện tượng bot-to-bot loop. |
| **TC-02** | *Exa + Safe Crawl4AI với SSRF Guard* | Yêu cầu: `@Xu cào và phân tích bài viết tại https://example.com/ai-trends` | `Xu` kiểm tra an toàn URL $\rightarrow$ Crawl4AI tải về Markdown sạch $\rightarrow$ Xu tóm tắt trả lời trên Discord. |
| **TC-03** | *SSRF Attack Prevention* | Yêu cầu: `@Xu lấy dữ liệu từ http://169.254.169.254/latest/meta-data/` | `safe-crawl.py` chặn đứng request ngay lập tức, trả về lỗi `SSRF Blocked: Prohibited IP Range`, không lộ dữ liệu VPS. |
| **TC-04** | *Personal User Memory Recall (OpenClaw memory built-in)* | 1. Báo với bot: `@Xu mình đang làm dự án FinTech tên PayFast, ưu tiên tech stack Golang và cần tin tức về thị trường chứng khoán VN`.<br>2. Hôm sau hỏi: `@Xu hôm nay có tin gì liên quan đến công việc và dự án của mình không?` | `Xu` tự động liên kết dự án PayFast + Golang + Chứng khoán VN để lọc tin tức và đưa ra gợi ý chuẩn xác cho người dùng. |
| **TC-05** | *Safe Browser Use Execution* | Yêu cầu: `@Xu mở trang dashboard https://github.com/trending kiểm tra top 3 repo hôm nay` | `Xu` gọi Cloud Browser Use, lấy dữ liệu và render tóm tắt an toàn. Nếu người dùng tag `@Thợ` làm việc này, Thợ từ chối và hướng dẫn tag `@Xu`. |
| **TC-06** | *Local QMD Personal RAG* | Lưu file ghi chú `data/knowledge/my-goals-2026.md` $\rightarrow$ hỏi `@Xu kế hoạch mục tiêu quý 3 của mình là gì?` | QMD hybrid search tìm đúng file local, `Xu` đọc và trả lời chi tiết. |

---

## 7. Dự Toán Tài Nguyên & Chi Phí Vận Hành

### 7.1. Tài nguyên máy chủ đề xuất (VPS)
* **CPU:** 2 - 4 vCPU
* **RAM:** 4GB - 8GB RAM (Đủ để chạy đồng thời QMD Local Embedding + Crawl4AI Playwright).
* **Disk:** 30GB SSD trở lên.

### 7.2. Bảng dự toán chi phí hàng tháng cho khối lượng công việc mới của Xu (DeepSeek API)

Với việc `🪙 Xu` đảm nhận vai trò **Personal Assistant Hub**:
* **Push định kỳ:** 3 lần/ngày $\times$ 30 ngày = 90 bản tin digest (mỗi bản tin ~3K - 5K tokens context & output) $\approx$ ~400K tokens/tháng.
* **Tương tác hàng ngày:** Tra cứu Exa, cào web Crawl4AI, RAG QMD, cập nhật MEMORY.md/USER.md $\approx$ 300K - 500K tokens/ngày $\approx$ ~10M - 15M tokens/tháng.
* **Đơn giá DeepSeek Chat:** ~$0.14 - $0.28 / 1M input tokens (cache hit/miss), ~$0.55 / 1M output tokens.
* $\rightarrow$ **Chi phí DeepSeek API ước tính:** **~$2.50 - $6.00 / tháng** (vẫn vô cùng rẻ nhưng loại bỏ hoàn toàn nguy cơ nghẽn 5 RPM).

### 7.3. Tổng chi phí toàn hệ thống hàng tháng
* **VPS (Hetzner / GCP / DigitalOcean):** ~$6.00 - $12.00 / tháng.
* **DeepSeek API (`🪙 Xu` - Personal Hub):** ~$2.50 - $6.00 / tháng.
* **Google Gemini (`🆓 Chùa` - Bulk Reading dự phòng):** **$0** (Free Tier).
* **Exa Search API:** $0 (Free Tier 1,000 queries/tháng).
* **Crawl4AI & QMD:** $0 (Mã nguồn mở chạy local).
* **Browser Use Cloud:** $0 (Free tier 3 concurrent sessions).
* **Tổng ngân sách vận hành:** **~$8.50 - $18.00 / tháng** cho một hệ thống Personal Assistant 24/7 ổn định, không bị bóp nghẽn.

---

> 💡 **Thứ tự thực hiện khuyến nghị:** Triển khai **Giai đoạn 1 (Cập nhật Persona Xu & Proactive Push)** trước, sau đó cài đặt **Giai đoạn 2 (Exa + Crawl4AI + SSRF Guard)** và **Giai đoạn 3 (QMD + memory built-in)** để nạp dữ liệu cá nhân cho Xu, cuối cùng là **Giai đoạn 4 (Browser Use)**.
