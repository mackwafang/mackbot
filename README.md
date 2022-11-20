# mackbot
The World of Warships (WoWS) Discord bot with ship build sharing and ship encyclopedia.

mackbot is designed to help new and existing players to be familiar with their warships, upgrades, or skills, while not in-game or while in a heated debate in their Discord server. 

##Invite mackbot
Invite mackbot to your server [here](https://discord.com/api/oauth2/authorize?client_id=667866391231332353&permissions=378880&scope=bot).

## Installation
After making a clone/fork, simply the following to install the necessary packages for mackbot to run:
```
pip3 install -r requirements.txt
```

## config.json
mackbot will require a file named `config.json` in the `data` directory, which will need to contain the following key/value pairs:
```
{
    "wg_token" : "WG_token_goes_here",
    "bot_token" : "discord_bot_token_goes_here",
    "sheet_id" : "optional_google_sheets_id_here",
    "bot_invite_url": "optional_discord_bot_invite_url_here",
    "mongodb_host": "optional_mongodb_url_here",
    "command_prefix": "mackbot",
    "discord_invite_url": "support_server_invite_url"
}
```

## Discord Commands
All usable commands can be found by using the command `mackbot help` in Discord, or in the `./data/help_command_strings.json`. You can enable/disable commands in the `./data/help_command_strings.json` file.

###mackbot's commands include, but not limited to:
- **build** (Get a ship build, via **mackbot build** or **/build**)
- **ship** (Get warship information, via **mackbot ship** or **/ship**)
- **show** (Display items in a category (e.g. ships, upgrades), via **mackbot show** or **/show**)
- **player** (Get player information, via **mackbot player** or **/player**)

## Discord server
mackbot has a [Discord server](https://discord.gg/3rt6n2SYWr) for all updates or support needs.

## Legal
All copyrighted materials owned by Wargaming.net. All rights reserved.\
All other contents are available under the MIT license.