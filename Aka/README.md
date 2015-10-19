## Requirements
 * <a href="http://znc.in">ZNC</a>
 * <a href="https://www.python.org">Python 3</a>
 * <a href="http://wiki.znc.in/Modpython">modpython</a>
 * <a href="http://docs.python-requests.org/en/latest/">python3-requests</a>
 * <a href="https://www.sqlite.org">sqlite3</a>

## Installation
To install aka, place aka.py in your ZNC modules folder

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

`seen nick <nick>` Displays last time user was seen speaking globally

`seen in <chan> <nick>` Displays last time user was seen speaking in channel

`geoip <host>` Geolocates the given host

`geoip <nick>` Geolocates a user by nick

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

 * **DEBUG_MODE** *(0/1)* Display raw output
 * **NOTIFY_ON_JOIN** *(0/1)* Automatically run `trace nick` when a user joins a channel
 * **NOTIFY_ON_JOIN_TIMEOUT** *(int: seconds)* How long to wait before sending notification again for same user
 * **NOTIFY_DEFAULT_MODE** *(nick/host)* Whether to use nick or host for on join trace
 * **NOTIFY_ON_MODE** *(0/1)* Automatically be notified when channel modes are changed
