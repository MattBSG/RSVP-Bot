# RSVP-Bot
WoW raid RSVP Discord Bot. This is a commissioned product; that being said, if you encounter a problem please open an issue and I can take a look if this is something you use. This repository has been tested to work on python 3.7.

## Setup
The first requirement is already have python3,7 or above and to download files for the bot and install their dependencies. Fire off a git clone in the directory you wish to encompass it like so:
```sh
$ git clone https://github.com/MattBSG/RSVP-Bot
$ cd RSVP-Bot/
$ pip install -r requirements.txt
```
It is highly encouraged to use a virtual environment as to not conflict with outside programs.

#### Get a Discord bot token
Head on over to https://discord.com/developers/ and click "New Application" in the top right corner. Give it a name and hit "Create". On the new page you are redirected to, add a App Icon and make a note of your `Client ID` -- we'll need it later.

On the left side pane, click "Bot" and then "Add Bot". Change the name if you want it to be named something else and untick "Public Bot" (unless you intend to allow others to add your bot to their server, with or without your permission). Scroll down a bit and tick "Server Members Intent". Now scroll back up to the top and make a note of your `Token` -- this will be how the bot logs into Discord.

With your `Client ID` in hand, replace "CLIENTID" in this link with your own, then visit the new link in a browser: https://discord.com/api/oauth2/authorize?client_id=CLIENTID&permissions=347200&scope=bot
This will allow you to add the bot to servers you have Manage Server permission in. Note: If you need someone else to add the bot for you, you must enable the "Public Bot" tick on the bot tab from before.

#### Edit the constants file
You'll next want to make some file changes. Head over to the directory the bot is in if you are not already there, and **make a copy** of `constants.py.example`, renaming the new file to `constants.py`. Edit `constants.py` and edit the relevent information which includes your bot application token you got from the steps above, the prefix that will be used for commands (i.e. "!" in "!help"), extra aliases for more timezones (if wanted), and your own emoji (you must replace the ones in the constants file, .they will not work for you).

#### Run the bot
To actually use the bot, you now need to run it. This assumes you have python already installed once again. Use the following command in either your shell or command prompt window to run the bot:
```sh
python bot.py
```

Next, run the `setup` command in a channel the bot can see, adding the prefix for the bot at the beginning of "setup". For example if your prefix is "!", then do "!setup". Follow the interactive instructions and you are setup. Now use the `help` command to see how use different commands in the bot. You're all set!
