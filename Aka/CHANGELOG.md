# Changelog

### Version 1.2.3 (2015-10-10):
  * Data directory automatically set

### Version 1.2.2 (2015-10-10):
  * Config is saved when you change a setting via ZNC

### Version 1.2.1 (2015-10-10):
  * Command validation for sub-commands

### Version 1.2.0 (2015-10-09):
  * Fixed typos
  * New command `nickchans` same thing as `hostchans` but with nicks
  * New command `version` tells the you version of the script

### Version 1.1.0 (2015-10-09):
  * New command `merge chans` combine someone else's \*\_chans.json with yours!
  * The script will now make you a config file if you don't already have one
  * Nick searches are now case-insensitive

### Version 1.0.0 (2015-10-09):
  * Code refactoring
  * Added checks to ensure all files and folders are created before loading
  * New command `merge hosts` combine someone else's \*\_hosts.json with yours!

### Version 0.2.2 (2015-10-08):
  * Spelling and grammar fixes

### Version 0.2.1 (2015-10-08):
  * Fixed FileNotFoundError bug.
  * You can now manually map nick to host
  * Code refactoring
  * Fixed a bug with `sharedchans` and `intersect`

### Version 0.2.0  (2015-10-04):
  * Config file is now pretty.
  * New command `hostchans` added. prints all the channels a host is in
  * New command `intersect` added.  prints all nicks that share channels
  * New command `sharedchans` added.  prints all channels shared by those nicks

### Version 0.0.2 (2015-10-04):
  * You can now manually save with `save`
  * You can now change the config within ZNC

### Version 0.0.1 (2015-09-27):
  * OnQuit() and OnPart() functions added
  * Trace outputs are now sorted.
  * Implemented a save timer
  * Now adds nicks when a `WHO` is done on a channel
  * Now adds nicks when a `WHOIS` is done on a user
  * Now adds nicks when a `WHOWAS` is done on a user
