# gen_scripts - Setup Scripts for Borderless

> Collection of scripts to generate tokens, credentials, and configure Google Drive access for the bot.

---

## Which Script Do You Need?

Use this flowchart to find the right script for your use case:

```
┌─────────────────────────────────────────────────────────────────┐
│                    What do you want to do?                     │
└─────────────────────────────────────────────────────────────────┘
                              │
            ┌─────────────────┼─────────────────┐
            ▼                 ▼                 ▼
    ┌───────────────┐  ┌─────────────┐  ┌─────────────────┐
    │  Telegram     │  │   Google    │  │  Configure      │
    │  Account      │  │   Drive     │  │  Drives         │
    └───────────────┘  └─────────────┘  └─────────────────┘
            │                 │                 │
            ▼                 ▼                 ▼
    ┌───────────────┐  ┌─────────────┐  ┌─────────────────┐
    │ gen_pyro_     │  │ Need token? │  │    driveid      │
    │ session       │  │    Yes      │  │                 │
    └───────────────┘  └─────────────┘  └─────────────────┘
                              │
                    ┌─────────┴─────────┐
                    ▼                   ▼
            ┌───────────────┐  ┌─────────────────────┐
            │generate_drive│  │ Already have token? │
            │_token        │  │    No               │
            └───────────────┘  └─────────────────────┘
                                        │
                    ┌───────────────────┴───────────────────┐
                    ▼                                       ▼
            ┌───────────────┐                      ┌───────────────┐
            │ Need SA for   │                      │ Add accounts  │
            │ Team Drive?   │                      │ to Team Drive │
            │   Yes         │                      │               │
            └───────────────┘                      └───────────────┘
                    │                                       │
                    ▼                                       ▼
            ┌───────────────┐                      ┌───────────────┐
            │gen_sa_accounts│                      │add_to_team_   │
            │               │                      │drive          │
            └───────────────┘                      └───────────────┘
```

---

## Quick Start for Beginners

### Scenario 1: First Time Setup

```
1. Generate Drive Token
   cd gen_scripts/gen_token_pickle
   python script.py

2. Configure Drives
   cd ../driveid
   python script.py

3. (Optional) Set up Telegram
   cd ../gen_pyro_session
   python script.py
```

### Scenario 2: Add Team Drive Access

```
1. Create Service Accounts (takes 15-30 mins)
   cd gen_scripts/gen_sa_accounts
   python script.py --quick-setup 5

2. Add Accounts to Team Drive
   cd ../add_to_team_drive
   python script.py --drive-id "YOUR_DRIVE_ID"
```

---

## Script Overview

| Script | Purpose | Complexity | Time |
|--------|---------|------------|------|
| [gen_token_pickle](./gen_token_pickle/) | Create Google OAuth token | Beginner | 1 min |
| [gen_pyro_session](./gen_pyro_session/) | Create Telegram session | Beginner | 2 min |
| [driveid](./driveid/) | Configure drives to search | Beginner | 2 min |
| [gen_sa_accounts](./gen_sa_accounts/) | Create service accounts | Advanced | 15-30 min |
| [add_to_team_drive](./add_to_team_drive/) | Add SAs to Team Drive | Advanced | 5 min |

---

## Directory Structure

```
gen_scripts/
├── README.md                    # This file
├── gen_token_pickle/
│   ├── README.md                # Documentation
│   └── script.py                # Token generator
├── gen_pyro_session/
│   ├── README.md
│   └── script.py                # Telegram session
├── driveid/
│   ├── README.md
│   └── script.py                # Drive configuration
├── gen_sa_accounts/
│   ├── README.md
│   └── script.py                # Service account generator
├── add_to_team_drive/
│   ├── README.md
│   └── script.py                # Add SAs to Team Drive
├── config/
│   ├── credentials.json         # OAuth credentials
│   └── requirements-cli.txt     # Python dependencies
└── tokens/
    ├── token.pickle             # Google Drive token
    └── token_sa.pickle           # SA token (created after use)
```

---

## Common Workflows

### Workflow 1: Basic Google Drive Setup

```
1. gen_token_pickle → Creates OAuth token
2. driveid              → Configures which drives to search
```

### Workflow 2: Full Team Drive Setup

```
1. gen_token_pickle     → Creates OAuth token
2. gen_sa_accounts --quick-setup N → Creates N projects with SAs
3. add_to_team_drive -d "ID" → Adds SAs to Team Drive
4. driveid                  → Adds Team Drive to search list
```

### Workflow 3: Telegram Only

```
1. gen_pyro_session → Creates Telegram session string
```

---

## Prerequisites

### Required Before Running Any Script

1. **Python 3.8+** installed
2. **Dependencies installed**:
   ```bash
   pip install -r config/requirements-cli.txt
   ```

### Per Script Requirements

| Script | Required |
|--------|----------|
| gen_token_pickle | Google credentials.json |
| gen_pyro_session | Telegram API key + hash from my.telegram.org |
| driveid | None |
| gen_sa_accounts | Google credentials.json (with APIs enabled) |
| add_to_team_drive | credentials.json + service accounts created |

---

## Getting Help

1. **For specific script**: See the README.md in each script folder
2. **For errors**: Check "Troubleshooting" section in each script's README
3. **For more help**: Open an issue on GitHub

---

## Related Documentation

- [Main Project README](../../README.md)
- [Bot Configuration Guide](../#configuration)
- [Google Cloud Setup Guide](https://console.cloud.google.com/)