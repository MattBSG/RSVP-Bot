# RSVP-Bot
WoW raid RSVP Discord Bot. This is a commissioned product; that being said, if you encounter a problem please open an issue and I can take a look if this is something you use. This repository has been tested to work on python 3.7.

![](https://cdn.mattbsg.xyz/jicJ5PfB6S.png)

## Commands
Arguments in brackets [] are optional, while ones in braces {} are required. Do not include the brackets or braces when running commands. This assumes your prefix is the default "?". You can change your prefix in your constants file. `Admin` roles are set during setup.

Command | Permissions | Description
------- | ----------- | -----------
`?setup` | Server or Bot Owner | Setup a server to work. Follow the prompts in chat. Must be the server owner or owner of the bot to run this, and it can be rerun at any time to make changes.
`?rsvp {day} {time} {timezone} {description}` | Admin | Creates a reservation. Day is a day of the week, i.e. thursday. Time is a 12hour time with am/pm, i.e. 1:46pm. Timezone is either an alias set in your constants file (such as "eastern" for America/New_York) or a full timezone string like America/Chicago. Easy way to find timezones [here](http://www.timezoneconverter.com/cgi-bin/findzone.tzc). The description is to tell members what the event the reservation is for.
`?rsvp alias {mode} {member} [alias]` | Admin |  Sets the alias of a user in a reservation -- embeds only update after there is a change to the rsvp (like if someone leaves, joins, or changes status). Mode will be either "set" or "clear". You must provide the member you are targeting, which is a mentiono or a user id. If you use "set", you'll need to provide what their alias should be, otherwise if you are clearing the alias with "clear" you only need to provide the member
`?rsvp cancel {message}` | Admin |  Cancel's an event/reservation. If you no longer want an event and would like to cancel it, you can provide either the message id or message link for the reservation
`?rsvp message {content}` | Admin |  Sets the message used to remind people to join before the raid begins. This reminder is sent at most 15 minutes before the event
`?rsvp recurr {message} {frequency}` | Admin |  Sets an event to recurr indefinitely, until stopped, on a provided schedule. Message is a reservation in either a message id or message link. Frequency is one of the following: "daily", "weekly", "biweekly"
`?rsvp recurr stop {message}` | Admin |  Stops an event from recurring in the future. You can provide a message id or message link for any reservation in the recurring series

## Setup
The first requirement is already have python3.7 or above and to download files for the bot and install their dependencies. Fire off a git clone in the directory you wish to encompass it like so:
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
