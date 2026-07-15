# Telegram Batch Command Sender

Windows desktop tool that reads TSV/CSV spreadsheet exports, generates the same `/concept` command blocks as `batch-tsv.htm`, and pastes them into **Telegram Desktop** or **Telegram Web** like a human would (clipboard + Ctrl+V + Enter).

No Telegram bot API and no bot-to-bot messaging.

## Requirements

- Windows 10/11
- Python 3.8 or newer (3.10, 3.11, 3.12, 3.13 all work)
- Telegram Desktop or Telegram Web open to your mod chat

## Setup

Open PowerShell in this folder:

```powershell
cd "d:\Editors\Vs code\Code\03_FiverrProjects\teleGramBot"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Run

```powershell
.\.venv\Scripts\Activate.ps1
python telegram_sender.py
```

## Usage

1. **Load data** — Click **Browse TSV/CSV...** and choose your export (e.g. `captain.tsv`), then **Load**.
2. **Configure**
   - **Cooldown** — seconds to wait between rows (or between individual commands in split mode).
   - **Start countdown** — seconds before sending starts so you can focus Telegram.
   - **Send mode**
     - *One message per row* — matches copying the whole textarea from `batch-tsv.htm`.
     - *One message per /concept command* — splits on `;;;` and sends each command separately.
3. **Focus Telegram** — Click the chat input in Telegram Desktop or Web.
4. **Start** — After the countdown, the tool pastes and sends automatically.
5. **Pause / Resume / Stop** — Control the run at any time. Progress is saved after each send.

## Progress & logs

| File | Purpose |
|------|---------|
| `sender_progress.json` | Saved row/command index for resume after stop or crash |
| `sender.log` | Timestamped run log |

Use **Reset progress** to clear saved state and start from row 1.

## Safety

- **Failsafe** — Move the mouse to any screen corner to abort immediately (PyAutoGUI default). Progress is saved.
- Do not use the keyboard/mouse while a run is active.
- Keep Telegram focused on the correct mod chat before the countdown ends.

## Spreadsheet format

Same columns as `batch-tsv.htm` (case-insensitive headers):

`type`, `nsfw`, `name`, `tags`, `huggingface`, `info`, `token`, `thumbnail`, `triggers`, `description`, `shardgroup`, `family`

Export from Google Sheets as **Tab-separated values (.tsv)** or CSV.

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Nothing pastes | Ensure Telegram chat input is focused before countdown ends |
| Wrong chat receives messages | Switch to the correct chat and restart |
| Paste is slow | Increase cooldown slightly |
| Permission errors on clipboard | Close other clipboard managers temporarily |

## Files

- `telegram_sender.py` — GUI + automation
- `command_generator.py` — TSV/CSV → command blocks (ported from `batch-tsv.htm`)
- `batch-tsv.htm` — original browser-based generator
- `captain.tsv` — sample data
