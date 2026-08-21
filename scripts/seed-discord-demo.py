#!/usr/bin/env python3
"""Seed a private Discord workspace with clearly marked demo messages.

Reads bot tokens from ~/.openclaw/openclaw.json on the VPS. This intentionally
does not print secrets and prefixes every message with [demo seed].
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from argparse import ArgumentParser


CHANNELS = {
    "general": "REDACTED_CHANNEL_ID",
    "research-desk": "REDACTED_CHANNEL_ID",
    "code-review": "REDACTED_CHANNEL_ID",
    "openclaw-config": "REDACTED_CHANNEL_ID",
    "video-maker": "REDACTED_CHANNEL_ID",
    "demo-stage": "REDACTED_CHANNEL_ID",
}


MESSAGES = [
    (
        "xu-bot",
        "general",
        "[demo seed] Sáng nay ưu tiên 3 việc: 1) chốt flow demo OpenClaw, "
        "2) giữ tech-video-maker làm artifact phụ, 3) không thêm bot mới nếu chưa có use-case rõ.",
    ),
    (
        "ve-thang-bot",
        "general",
        "[demo seed] Nếu ai hỏi OpenClaw khác chatbot ở đâu: chatbot trả lời trong ô chat; "
        "OpenClaw biến Discord thành cửa điều phối agent + tool + workspace.",
    ),
    (
        "chua-bot",
        "research-desk",
        "[demo seed] Research note: so sánh OpenClaw với chatbot nên tránh nói tuyệt đối. "
        "Chatbot hiện đại cũng có tool/memory; điểm khác nằm ở gateway tự host, routing, workspace và quyền.",
    ),
    (
        "xu-bot",
        "research-desk",
        "[demo seed] Câu cần kiểm chứng trước sân khấu: self-hosted không đồng nghĩa dữ liệu không rời máy. "
        "Model provider, Discord, search API và tool bên ngoài vẫn có thể nhận dữ liệu.",
    ),
    (
        "ve-thang-bot",
        "research-desk",
        "[demo seed] Handoff cho bài nói: dùng ví dụ AI từng bịa ngày lễ để giải thích vì sao 3 bot phản biện nhau "
        "bắt được góc nhìn, nhưng không tự bảo đảm đúng sự kiện.",
    ),
    (
        "thoi-bot",
        "openclaw-config",
        "[demo seed] VPS status note: render video nên chạy trên máy scale-up. 2 vCPU render full HD quá chậm; "
        "8 vCPU + Remotion concurrency 6 cho tốc độ hợp lý hơn.",
    ),
    (
        "xu-bot",
        "openclaw-config",
        "[demo seed] Quy tắc bảo mật đang giữ: private guild + user allowlist là hàng rào chính. "
        "Không dựa vào channel allowlist vì thêm channel mới dễ quên cập nhật làm bot im lặng.",
    ),
    (
        "ve-thang-bot",
        "openclaw-config",
        "[demo seed] Decision: bỏ Perplexity bot khỏi core demo. Nếu search bridge không trả nguồn tốt hơn web/app chính, "
        "không nên để nó làm nhân vật chính trong phòng.",
    ),
    (
        "thoi-bot",
        "code-review",
        "[demo seed] Review note: tech-video-maker vừa vá 2 nhóm lỗi đáng demo: facts JSON AI sinh lệch schema "
        "và Remotion thiếu optional native binding @rspack trên VPS.",
    ),
    (
        "ve-thang-bot",
        "code-review",
        "[demo seed] Code health: gate hiện có check.mjs + verify-script.mjs + facts normalization. "
        "Điểm nên làm sau: preview render 720p để demo nhanh, không chờ bản full.",
    ),
    (
        "ve-thang-bot",
        "video-maker",
        "[demo seed] Video artifact mới: openclaw-khac-chatbot-nhieu-khong.mp4 đã render xong, "
        "có 10 scene, master về -14 LUFS và có frame preview trong gallery.",
    ),
    (
        "thoi-bot",
        "video-maker",
        "[demo seed] Render lesson: TTS không phải bottleneck sau khi cache audio. "
        "Bottleneck chính là Chromium/Remotion render full HD; tăng vCPU có tác dụng rõ.",
    ),
    (
        "xu-bot",
        "video-maker",
        "[demo seed] Kịch bản video nên giữ giọng thật thà: OpenClaw không phải phép màu, "
        "nhưng là cách biến nơi chat thành bàn điều phối công việc có state, tool và trách nhiệm.",
    ),
    (
        "xu-bot",
        "demo-stage",
        "[demo seed] Demo rehearsal flow: 1) hỏi mơ hồ trong #general, 2) đẩy research sang #research-desk, "
        "3) chốt rủi ro ở #openclaw-config, 4) mở video artifact ở #video-maker.",
    ),
    (
        "ve-thang-bot",
        "demo-stage",
        "[demo seed] Opening line gợi ý: Mình không demo một con chatbot thông minh hơn. "
        "Mình demo cách biến Discord riêng thành một phòng làm việc có người ghi nhớ, phản biện và chạy việc.",
    ),
]


def load_accounts() -> dict:
    config_path = os.path.expanduser("~/.openclaw/openclaw.json")
    with open(config_path, "r", encoding="utf-8") as handle:
        config = json.load(handle)
    return config["channels"]["discord"]["accounts"]


def send_message(accounts: dict, account_id: str, channel_name: str, content: str) -> tuple[bool, str]:
    token = accounts.get(account_id, {}).get("token")
    if not token:
        return False, f"missing token for {account_id}"

    url = f"https://discord.com/api/v10/channels/{CHANNELS[channel_name]}/messages"
    payload = json.dumps(
        {"content": content, "allowed_mentions": {"parse": []}},
        ensure_ascii=False,
    ).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=payload,
        method="POST",
        headers={
            "Authorization": f"Bot {token}",
            "Content-Type": "application/json",
            "User-Agent": "oeditions-demo-seeder/1.0",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            body = json.loads(response.read().decode("utf-8"))
            return True, body.get("id", "")
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", "replace")[:500]
        return False, f"HTTP {error.code}: {detail}"
    except Exception as error:  # pragma: no cover - operational script
        return False, repr(error)


def parse_args() -> object:
    parser = ArgumentParser(description="Seed the private Discord server with marked demo messages.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the planned messages without sending them.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.dry_run:
        for index, (account_id, channel_name, content) in enumerate(MESSAGES, 1):
            print(f"{index:02d} {account_id} -> #{channel_name}: {content}")
        return 0

    accounts = load_accounts()
    sent = 0
    for index, (account_id, channel_name, content) in enumerate(MESSAGES, 1):
        ok, result = send_message(accounts, account_id, channel_name, content)
        status = "OK" if ok else "FAIL"
        print(f"{index:02d} {status} {account_id} -> #{channel_name}: {result}")
        sent += int(ok)
        time.sleep(0.8)
    print(f"sent {sent}/{len(MESSAGES)} demo seed messages")
    return 0 if sent == len(MESSAGES) else 1


if __name__ == "__main__":
    sys.exit(main())
