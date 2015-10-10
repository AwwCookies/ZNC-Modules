# Changelog

### Version 1.1
  * OnQuit() and OnPart() functions added
  * Trace outputs are now sorted
  * Implemented a save timer
  * Now adds nicks when a `WHO` is done on a channel
  * Now adds nicks when a `WHOIS` is done on a user
  * Now adds nicks when a `WHOWAS` is done on a user

### Version 1.2:
  * You can now manually save with `save`
  * You can now change the config within ZNC

### Version 2.0:
  * Config file is now pretty.
  * New command `hostchans` added. prints all the channels a host is in
  * New command `intersect` added.  prints all nicks that share channels
  * New command `sharedchans` added.  prints all channels shared by those nicks

### Version 2.1:
  * Fixed FileNotFoundError bug.
  * You can now manually map nick to host
  * Code refactoring
  * Fixed a bug with sharedchans and intersect
  * Fixed some syntax errors

### Version 3.0:
  * Code refactoring
  * Added checks to ensure all files and folders are created before loading
  * New command `marge hosts` combine someone else's *_hosts.json with yours!
