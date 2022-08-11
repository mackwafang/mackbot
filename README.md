# mackbot
The World of Warships (WoWS) Discord bot with ship build sharing and ship encyclopedia.

Invite mackbot [here](https://discord.com/api/oauth2/authorize?client_id=667866391231332353&permissions=378880&scope=bot).

mackbot now has a web application with limited capabilities at https://mackbot-web.herokuapp.com/

## Installation
After making a clone/fork, simply the following to install the necessary packages for mackbot to run:
```
pip3 install -r requirements.txt
```

## config.json
mackbot will require a file named `config.json` which will need to contain the following key/value pairs:
```
{
  "wg_token": wg_api_token_here,
  "bot_token": discord_bot_token_here,
  "sheet_id": optional_token_for_google_sheets_fetching,
  "bot_invite_url": discord_bot_invite_url_here
}
```
- **wg_token**: Required for gathering some information (such as the **player** command) from WG.
- **bot_token**: Required to run the bot
- **sheet_id**: Optional for fetching from a Google Sheet where you can crowdsource your ship builds.
- **bot_invite_url**: Optional for the **invite** command.

## Discord Commands
All usable commands can be found by using the command `mackbot help` in Discord, or in the `./help_command_strings.json`. You can enable/disable commands in the `./help_command_strings.json` file.

mackbot's commands include, but not limited to:
- **build** (Get a ship build)
- **ship** (Get warship information)
- **show** (Display items in a category (e.g. ships, upgrades))
- **player** (Get player information)


### Legal
All copyrighted materials owned by Wargaming.net. All rights reserved.\
All other contents are available under the MIT license.