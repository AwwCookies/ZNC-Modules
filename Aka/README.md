## Branches

**Two (2) branches of aka currently exist, both of which are supported:**

 * `master` is the original module, with all basic features and tracking
 * `sqlite` is a rewrite of the JSON (master) version to use SQL (sqlite) data storage instead. It contains additional features and capabilities.

*Migration of data from `master` to `sqlite` is automatic. Original data files are preserved, although new SQL data migration back to JSON is **not** currently supported.*

Please note that requirements differ slighty. Please read the Requirements section carefully.

## Requirements
 * <a href="http://znc.in">ZNC</a>
 * <a href="https://www.python.org">Python 3</a>
 * <a href="http://wiki.znc.in/Modpython">modpython</a>
 * <a href="http://docs.python-requests.org/en/latest/">python3-requests</a>

## Installation
To install Aka, place Aka.py in your ZNC modules folder

## Loading
Aka must be loaded on each network you wish to use it on
`/msg *status loadmod Aka`

## `trace` Commands

`nick <nick>` Shows nick change and host history for given nick

`sharedchans <nick1> <nick2> ... <nick#>` Show common channels between a list of users

`intersect <#channel1> <#channel2> ... <#channel#>` Display users common to a list of channels

`nickchans <nick>` Get all channels a nick has been seen in

`hostchans <host>` Get all channels a host has been seen in

## User Info Commands

`geoip <host>` Geolocates the given host

`geoip <nick` Geolocates a user by nick

## Modify Data Commands

`add <nick> <host>` Manually add a nick/host entry to the database

`save` Manually save the latest tracks to disk

`merge hosts <url>` Merges the **hosts** files from two users

`merge chans <url>` Merges the **chans** files from two users

## Other Commands

`info` Display information about the module

`version` Get current module version

`getconfig` Print current network configuration

`config <variable> <value>` Set configuration variables

`stats` Print nick and host stats for the network

`update` Updates Aka to the newest version

`help` Print help from the module

## Configuration Variables

 * **SAVE_EVERY** *(seconds)* How often changes are written to disk
 * **TEMP_FILES** *(0/1)* Whether or not data is stored in temp files or written directly to save files
 * **DEBUG_MODE** *(0/1)* Display raw output
 * **NOTIFY_ON_JOIN** *(0/1)* Automatically run `trace nick` when a user joins a channel
 * **NOTIFY_ON_JOIN_TIMEOUT** *(int: seconds)* How long to wait before sending notification again for same user
 * **NOTIFY_DEFAULT_MODE** *(nick/host)*

## Contact

Issues/bugs should be submitted on the <a href="https://github.com/AwwCookies/ZNC-Modules/issues">GitHub issues page</a>.

For assistance, please e-mail AwwCookies (Aww) at <a href="mailto:aww@smile.sh">aww@smile.sh<a> or PM MuffinMedic (Evan) on <a href="https://kiwiirc.com/client/irc.freenode.net:+6697">freenode<a/> or <a href="https://kiwiirc.com/client/irc.snoonet.org:+6697">Snoonet<a>.
