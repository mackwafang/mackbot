# mackbot
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

The World of Warships (WoWS) Discord bot with ship build sharing and ship encyclopedia.

## Installation
Simply run:
```
pip3 install -r requirements.txt
```

## config.json
mackbot will require a file named `config.json` which will need to contain the following key/value pairs:
```
{
  wg_token: your_wg_token_here,
  bot_token: your_discord_bot_token_here,
  sheet_id: optional_token_for_google_sheets_fetching
}
```
- **wg_token**: Required for gathering some information (such as the **player** command) from WG.
- **bot_token**: Required to run the bot
- **sheet_id**: Optional for fetching from a Google Sheet where you can crowdsource your ship builds.

## Discord Commands
All usable commands can be found by using the command `mackbot help` in Discord, or in the `./help_command_strings.json`. You can enable/disable commands in the `./help_command_strings.json` file.

mackbot's commands include, but not limited to:
- **build** (Get a ship build)
- **ship** (Get warship information)
- **show** (Display items in a category (e.g. ships, upgrades))
- **player** (Get player information)


### Legal

© Wargaming.net. All rights reserved