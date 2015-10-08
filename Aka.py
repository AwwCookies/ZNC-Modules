# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
#   Author: AwwCookies (Aww)                                                  #
#   Last Update: Oct 8th 2015                                                 #
#   Version: 2.1                                                          # # #
#   Desc: A ZNC Module to track nicks                                     # #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# Changelog:
# Version 1.1:
#   OnQuit() and OnPart() functions added
#   Trace outputs are now sorted.
#   Implmemnted a save timer
#   Now adds nicks when a WHO is done on a channel
#   Now adds nicks when a WHOIS is done on a user
#   Now adds nicks when a WHOWAS is done on a user
# Version 1.2:
#   You can now manually save with `save`
#   You can now change the config within ZNC
# Version 2.0:
#   Config file is now pretty.
#   New command hostchans added. prints all the channels a host is in
#   New command intersect added.  prints all nicks that share channels
#   New command sharedchans added.  prints all channels shared by those nicks
# Version 2.1:
# Fixed FileNotFoundError bug.
# You can now manually map nick to host
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

import znc
import os
import json
import socket
import itertools

#CHANGE THIS TO THE USERNAME ZNC RUNS AS
USERNAME = "znc"
CONFIG = {
    "SAVE_EVERY": 60 * 5 # 5 mins
}

class SaveTimer(znc.Timer):
    def RunJob(self):
        self.GetModule().save()

class Aka(znc.Module):
    description = "aka tracking script"
    def OnLoad(self, args, message):
        self.USER = self.GetUser().GetUserName()
        self.NETWORK = self.GetNetwork().GetName()
        self.MODFOLDER = "/home/" + USERNAME + "/.znc/users/" + self.USER + "/moddata/Aka/"
        if os.path.exists(self.MODFOLDER + "config.json"):
            global CONFIG
            CONFIG = json.loads(open(self.MODFOLDER + "config.json").read())
        self.hosts = {}
        if not os.path.exists(self.MODFOLDER + self.NETWORK + "_hosts.json"):
            if not os.path.exists(self.MODFOLDER):
                os.mkdir(self.MODFOLDER)
            with open(self.MODFOLDER + self.NETWORK + "_hosts.json", 'w') as f:
                f.write(json.dumps(self.hosts))
        else:
            self.hosts = json.loads(open(self.MODFOLDER + self.NETWORK + "_hosts.json", 'r').read())
        self.channels = {}
        if not os.path.exists(self.MODFOLDER + self.NETWORK + "_chans.json"):
            with open(self.MODFOLDER + self.NETWORK + "_chans.json", 'w') as f:
                f.write(json.dumps(self.channels))
        else:
            self.channels = json.loads(open(self.MODFOLDER + self.NETWORK + "_chans.json", 'r').read())

        self.timer = self.CreateTimer(SaveTimer)
        self.timer.Start(CONFIG.get(SAVE_EVERY, 60 * 5))
        return True

    def process(self, host, nick):
        if host not in self.hosts:
            self.hosts[host] = []
            self.hosts[host].append(nick)
        else:
            if nick not in self.hosts[host]:
                self.hosts[host].append(nick)

    def process_chan(self, host, nick, channel):
        if channel not in self.channels:
            self.channels[channel] = []
            self.channels[channel].append((nick, host))
        else:
            if (nick, host) not in self.channels[channel]:
                self.channels[channel].append((nick, host))

    def OnRaw(self, message):
        if str(message.s).split()[1] == "352": # on WHO
            host = str(message.s).split()[5]
            nick = str(message.s).split()[7]
            channel = str(message.s).split()[3]
            self.process(host, nick)
            self.process_chan(host, nick, channel)
        elif str(message.s).split()[1] == "311": # on WHOIS
            host = str(message.s).split()[5]
            nick = str(message.s).split()[3]
            self.process(host, nick)
        elif str(message.s).split()[1] == "314": # on WHOWAS
            host = str(message.s).split()[5]
            nick = str(message.s).split()[3]
            self.process(host, nick)

    def OnJoin(self, user, channel):
        self.process(user.GetHost(), user.GetNick())
        self.process_chan(user.GetHost(), user.GetNick(), channel.GetName())

    def OnNick(self, user, new_nick, channels):
        self.process(user.GetHost(), new_nick)
        self.process_chan(user.GetHost(), user.GetNick(), channel.GetName())

    def OnPart(self, user, channel, message):
        self.process(user.GetHost(), user.GetNick())
        self.process_chan(user.GetHost(), user.GetNick(), channel.GetName())

    def OnQuit(self, user, channel, message):
        self.process(user.GetHost(), user.GetNick())
        self.process_chan(user.GetHost(), user.GetNick(), channel.GetName())

    def OnModCommand(self, command):
        cmds = ["trace", "help", "config", "save", "add"]
        if command.split()[0] in cmds:
            if command.split()[0] == "trace":
                if command.split()[1] == "sharedchans":
                    nicks = command.split()[2:]
                    chan_list = []
                    for nick in nicks:
                        chans = []
                        for chan in self.channels:
                            for user in self.channels[chan]:
                                if nick == user[0]:
                                    chans.append(chan)
                        chan_list.append(chans)
                    common = [item for item in set(itertools.chain(*chan_list))]
                    if common:
                        self.PutModule("Common channels %s" % (' '.join(common)))
                    else:
                        self.PutModule("No comman channels.")
                elif command.split()[1] == "intersect":
                    chans = command.split()[2:]
                    for chan in chans:
                        if chan not in self.channels:
                            self.PutModule("Invalid channel %s" % chan)
                    nick_list = []
                    for chan in chans:
                        nicks = []
                        for user in self.channels[chan]:
                            nicks.append(user[0])
                        nick_list.append(nicks)
                    common = [item for item in set(itertools.chain(*nick_list))]
                    if common:
                        self.PutModule("%s share those channels" % ', '.join(common))
                    else:
                        self.PutModule("No shared nicks" % ' '.join(common))
                elif command.split()[1] == "hostchans":
                    found = []
                    host = command.split()[2]
                    for chan in self.channels:
                        for user in self.channels[chan]:
                            if host == user[1]:
                                found.append(chan)
                    if found:
                        self.PutModule("%s was found in %s" % (host, ' '.join(found)))
                    else:
                        self.PutModule("%s was not found in any channels." % (host))
                elif command.split()[1] == "nick": # trace nick $nick
                    nick = command.split()[2]
                    hosts = 0
                    for host in self.hosts:
                        if nick in self.hosts[host]:
                            hosts += 1
                            self.PutModule("%s was also know as: %s (%s)" %(
                                nick, ', '.join(sorted(self.hosts[host])), host))
                    if not hosts:
                        self.PutModule("No nicks found for %s" % nick)
                elif command.split()[1] == "host": # trace host $host
                    host = command.split()[2]
                    if host in self.hosts:
                        self.PutModule("%s was also know as: %s" %(
                            host, ', '.join(sorted(self.hosts[host]))))
                    else:
                        self.PutModule("No nicks found for %s" % host)
            elif command.split()[0] == "save":
                self.save()
                self.PutModule("Saved.")
            elif command.split()[0] == "config":
                var_name = command.split()[1]
                value = command.split()[2]
                self.change_config(var_name, value)
            elif command.split()[0] == "add":
                nick = command.split()[1]
                host = command.split()[2]
                self.process(host, nick)

            elif command.split()[0] == "help":
                self.PutModule("trace nick $nick")
                self.PutModule("Example: trace nick Aww")
                self.PutModule("trace host $host")
                self.PutModule("Example: trace host 127.0.0.1")
                self.PutModule("Example: trace host example.com")
                self.PutModule("Save")
        else:
            self.PutModule("%s is not a valid command." % command)

    def save(self):
        with open(self.MODFOLDER + self.NETWORK + "_hosts.json", 'w') as f:
            f.write(json.dumps(self.hosts, sort_keys=True, indent=4))
        with open(self.MODFOLDER + self.NETWORK + "_chans.json", 'w') as f:
            f.write(json.dumps(self.channels, sort_keys=True, indent=4))

    def change_config(self, var_name, value):
        if var_name in CONFIG:
            if var_name == "SAVE_EVERY":
                if int(value) > 1:
                    CONFIG["SAVE_EVERY"] = int(value)
                    self.timer.Stop()
                    self.timer.Start(CONFIG["SAVE_EVERY"])
                    self.PutModule("%s => %s" % (var_name, str(value)))
                else:
                    self.PutModule("Please use a int value larger than 0")
            with open(self.MODFOLDER + "config.json", 'w') as f:
                f.write(json.dumps(CONFIG, sort_keys=True, indent=4))
            return True
        else:
            self.PutModule("%s is not a valid var." % command.split()[1])
            return False
