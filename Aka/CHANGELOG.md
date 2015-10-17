# Changelog

### Version 0.0.1:
  * OnQuit() and OnPart() functions added
  * Trace outputs are now sorted.
  * Implemented a save timer
  * Now adds nicks when a `WHO` is done on a channel
  * Now adds nicks when a `WHOIS` is done on a user
  * Now adds nicks when a `WHOWAS` is done on a user

### Version 0.0.2:
  * You can now manually save with `save`
  * You can now change the config within ZNC

### Version 0.2.0:
  * Config file is now pretty.
  * New command `hostchans` added. Prints all the channels a host is in
  * New command `intersect` added. Prints all nicks that share channels
  * New command `sharedchans` added. Prints all channels shared by those nicks

### Version 0.2.1:
  * Fixed FileNotFoundError bug.
  * You can now manually map nick to host
  * Code refactoring
  * fixed a bug with `sharedchans` and `intersect`

### Version 0.2.2:
  * Spelling and grammar fixes

### Version 1.0.0:
  * Public release
  * Code refactoring
  * Added checks to ensure all files and folders are created before loading
  * New command `merge hosts` combine someone else's \*\_hosts.json with yours!

### Version 1.1.0:
  * New command `merge chans` combine someone else's \*\_chans.json with yours!
  * The script will now make you a config file if you don't already have one
  * Nick searches are now case-insensitive

### Version 1.2.0:
  * Fixed typos
  * New command `nickchans` same thing as `hostchans` but with nicks
  * New command `version` tells the you version of the script

### Version 1.2.1:
  * Command validation for sub-commands

### Version 1.2.2:
  * Config is saved when you change a setting via ZNC

### Version 1.2.3:
  * You no longer need to specify the user in the file
  * New command `stats` tell you how many users/hosts you have added to your hosts.json

### Version 1.2.4
  * Fixed initialization error

### Version 1.2.5
  * Spelling fixes *(Credit: @Equinox)*

### Version 1.2.6
  * Added nick and channel inputs to intersect and sharedchans output

### Version 1.3.0
  * Added `help` output
  * Added `info` command

### Version 1.3.1
  * Added wiki page to module

### Version 1.4.0
  * Added option to automatically run `trace nick` for users on channel join
  * New variable to set limit on notification frequency for a given nick
  * Adds new config variables to file
  * Fixed config variable bug

### Version 1.4.1
  * Clarified `trace` commands in `help`

### Version 1.5.0
  * New 'update' command to auto-update from master

### Version 1.5.1
  * Relocated save files to proper location
  * Added on join `trace` for new users

### Version 1.5.2
  * Added `geoip <host>` command
  * Module reloads after `update`
  * Fixed OnNick and OnQuit bug *(Credit: @KindOne-)*

### Version 1.5.3
  * Fixed reload on `update`
  * `update` limited to administrators
  * `geoip <nick>` added
  * Bug fixes
