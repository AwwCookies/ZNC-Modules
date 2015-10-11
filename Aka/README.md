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

`nickchans <nick` Get all channels a nick has been seen in

`hostchans <host>` Get all channels a host has been seen in

## Modify Data Commands

`add <nick> <host>` Manually add a nick/host entry to the database

`save` Manually save the latest tracks to disk

`merge hosts <url>` Merges the **hosts** files from two users

`merge chans <url>` Merges the **chans** files from two users

## Other Commands

`config <variable> <value>` Set configuration variables

`help` Print help from the module

`stats` Print nick and host stats for the network
