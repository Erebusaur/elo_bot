# Elo Bot

## Download project

`git clone https://github.com/lfenart/elo_bot.git`

## Install dependencies

### python 3

https://www.python.org/downloads/

Additional libraries
```
py -3 -m pip install -U python-dotenv
py -3 -m pip install -U discord.py
py -3 -m pip install -U requests
py -3 -m pip install -U trueskill
```

### .Net Core 3.1

https://dotnet.microsoft.com/download/dotnet-core/3.1

## Set up the bot

In bot, rename .env.example to .env and write the discord token of your bot next to DISCORD_TOKEN.

## Run

Before the first execution, run `init.bat` to create the database. Do not run if afterwards as if will overwrite the old database.

Start the api first: `start_api.bat`

Then start the bot: `start_bot.bat`
