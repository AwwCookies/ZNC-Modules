#### `trace` Commands

`nick <nick>`

`sharedchans <nick1> <nick2> ... <nick#>` Show common channels between a list of users

`intersect <#channel1> <#channel2> ... <#channel#>` Display users common to a list of channels

`hostchans <host>` Get all channels a host has been seen in

#### Modify Data Commands

`add <nick> <host>` Manually add a nick/host entry to the database

`save` Manually save the latest tracks to disk

`merge hosts <url>` Merges the **hosts** files from two users

`merge chans <url>` Merges the **chans** files from two users

#### Other Commands

`config <variable> <value` Set configuration variables

`help` Print help from the module

`stats` Print nick and host stats for the network
