# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
#   Author: AwwCookies (Aww)                                          #
#   Last Update: Oct 10th 2015                                        #
#   Version: 1.3.0                                               # # #
#   Desc: A ZNC Module to track nicks                             # #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

import znc
import os
import json
import socket
import itertools

import requests

CONFIG = {
    "SAVE_EVERY": 60 * 5, # 5 mins
    "TEMP_FILES": False,
    "DEBUG_MODE": False
}

class SaveTimer(znc.Timer):
    def RunJob(self):
        self.GetModule().save()

class Aka(znc.Module):
    description = "Tracks nicks and hosts, allowing tracing and history viewing"
    def OnLoad(self, args, message):
        self.USER = self.GetUser().GetUserName()
        self.NETWORK = self.GetNetwork().GetName()
        self.MODFOLDER = znc.CUser(self.USER).GetUserPath() + "/moddata/Aka/"
        if os.path.exists(self.MODFOLDER + "config.json"):
            global CONFIG
            CONFIG = json.loads(open(self.MODFOLDER + "config.json").read())
        else:
            with open(self.MODFOLDER + "config.json", 'w') as f:
                f.write(json.dumps(CONFIG, sort_keys=True, indent=4))
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
        self.timer.Start(CONFIG.get("SAVE_EVERY", 60 * 5))

        # Do some checks
        if not os.path.exists(self.MODFOLDER):
            self.PutModule("Missing MODFOLDER")
            return False
        if not os.path.exists(self.MODFOLDER + "config.json"):
            self.PutModule("Missing config file")
            return False
        if not os.path.exists(self.MODFOLDER + self.NETWORK + "_hosts.json"):
            self.PutModule("%s_hosts.json file was not created" % self.NETWORK)
            return False
        if not os.path.exists(self.MODFOLDER + self.NETWORK + "_chans.json"):
            self.PutModule("%s_hosts.json file was not created" % self.NETWORK)
            return False
        # If there was no problems setting up then load the script
        return True

    def process(self, host, nick):
        if CONFIG.get("DEBUG_MODE", False):
            self.PutModule("DEBUG: Adding %s => %s" % (nick, host))
        if host not in self.hosts:
            self.hosts[host] = []
            self.hosts[host].append(nick)
        else:
            if nick not in self.hosts[host]:
                self.hosts[host].append(nick)

    def process_chan(self, host, nick, channel):
        if CONFIG.get("DEBUG_MODE", False):
            self.PutModule("DEBUG: Adding %s => (%s, %s)" % (channel, nick, host))
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

    def cmd_trace_sharedchans(self, nicks):
        nick_list = []
        chan_list = []
        for nick in nicks:
            nick_list.append(nick)
            chans = []
            for chan in self.channels:
                for user in self.channels[chan]:
                    if nick.lower() == user[0].lower():
                        chans.append(chan)
            chan_list.append(chans)
            common = [item for item in set(
                itertools.chain(*chan_list)) if all(
                    item in lst for lst in chan_list)]
        nick_list = ' '.join(sorted(set(nick_list), key=str.lower))
        chan_list = ' '.join(sorted(set(common), key=str.lower))

        if common:
            self.PutModule("Common channels between %s: %s" % (nick_list, chan_list))
        else:
            self.PutModule("No common channels.")

    def cmd_trace_intersect(self, chans):
        nick_list = []
        chan_list = []
        for chan in chans:
            if chan not in self.channels:
                self.PutModule("Invalid channel %s" % chan)

        for chan in chans:
            chan_list.append(chan)
            nicks = []
            for user in self.channels[chan]:
                nicks.append(user[0])
            nick_list.append(nicks)
        common = [item for item in set(
                        itertools.chain(*nick_list)) if all(
                            item in lst for lst in nick_list)]
        chan_list = ' '.join(sorted(set(chan_list), key=str.lower))
        nick_list = ' '.join(sorted(set(common), key=str.lower))

        if common:
            self.PutModule("Shared users between %s: %s" % (chan_list, nick_list))
        else:
            self.PutModule("No shared nicks" % ' '.join(sort(set(common), key=str.lower)))

    def cmd_trace_hostchans(self, host):
        found = []
        for chan in self.channels:
            for user in self.channels[chan]:
                if host == user[1]:
                    found.append(chan)
        if found:
            self.PutModule("%s was found in %s" % (host, ' '.join(sorted(set(found), key=str.lower))))
        else:
            self.PutModule("%s was not found in any channels." % (host))

    def cmd_trace_nickchans(self, nick):
        found = []
        for chan in self.channels:
            for user in self.channels[chan]:
                if nick.lower() == user[0].lower():
                    found.append(chan)
        if found:
            self.PutModule("%s was found in %s" % (nick, ' '.join(sorted(set(found), key=str.lower))))
        else:
            self.PutModule("%s was not found in any channels." % (host))

    def cmd_trace_nick(self, nick):
        hosts = 0
        for host in sorted(self.hosts):
            if nick.lower() in [n.lower() for n in self.hosts[host]]:
                hosts += 1
                self.PutModule("%s was also known as: %s (%s)" %(
                    nick, ', '.join(sorted(set(self.hosts[host]), key=str.lower)), host))
        if not hosts:
            self.PutModule("No nicks found for %s" % nick)

    def cmd_trace_host(self, host):
        if host in self.hosts:
            self.PutModule("%s was also known as: %s" %(
                host, ', '.join(sorted(set(self.hosts[host]), key=str.lower))))
        else:
            self.PutModule("No nicks found for %s" % host)

    def cmd_version(self):
        """
        Pull the version number from line 4 of this script
        """
        self.PutModule(open(__file__, 'r').readlines()[3].replace("#", "").strip())

    def cmd_save(self):
        self.save()
        self.PutModule("Saved.")

    def cmd_config(self, var_name, value):
        self.change_config(var_name, value)

    def cmd_add(self, nick, host):
        self.process(host, nick)
        self.PutModule("%s => %s" % (nick, host))

    def cmd_merge_hosts(self, URL):
        """
        Consolidates two *_hosts.json files
        """
        nicks = 0
        hosts = 0
        idata = json.loads(requests.get(URL).text)
        for host in idata:
            if host in self.hosts:
                for nick in idata[host]:
                    if not nick in self.hosts[host]:
                        self.hosts[host].append(nick)
                        nicks += 1
            else:
                self.hosts[host] = idata[host]
                hosts += 1
                nicks += len(idata[host])
        self.PutModule("%s nicks imported" % "{:,}".format(nicks))
        self.PutModule("%s hosts imported" % "{:,}".format(hosts))
        self.save()

    def cmd_merge_chans(self, URL):
        """
        Consolidates two *_chans.json files
        """
        chans = 0
        users = 0
        idata = json.loads(requests.get(URL).text)
        for channel in idata:
            if channel in self.channels:
                for user in idata[channel]:
                    if not user in self.channels[channel]:
                        self.channels[channel].append(user)
                        users += 1
            else:
                self.channels[channel] = idata[channel]
                chans += 1
                users += len(idata[channel])
        self.PutModule("%s users imported" % "{:,}".format(users))
        self.PutModule("%s channels imported" % "{:,}".format(chans))
        self.save()

    def cmd_info(self):
        self.PutModule("Aka nick tracking module by AwwCookies (Aww) - http://wiki.znc.in/Aka")

#    def cmd_help(self):
#        self.PutModule("https://github.com/AwwCookies/ZNC-Modules/blob/master/Aka/README.md")

    def cmd_stats(self):
        nicks = 0
        for host in self.hosts:
            nicks += len(self.hosts[host])
        self.PutModule("Nicks: %s" % "{:,}".format(nicks))
        self.PutModule("Hosts: %s" % "{:,}".format(len(self.hosts)))

    def OnModCommand(self, command):
        # Valid Commands
        cmds = ["trace", "help", "config", "info", "save", "add", "merge", "version", "stats"]
        if command.split()[0] in cmds:
            if command.split()[0] == "trace":
                cmds = ["sharedchans", "intersect", "hostchans", "nickchans", "nick", "host"]
                if command.split()[1] in cmds:
                    if command.split()[1] == "sharedchans":
                        self.cmd_trace_sharedchans(list(command.split()[2:]))
                    elif command.split()[1] == "intersect":
                        self.cmd_trace_intersect(command.split()[2:])
                    elif command.split()[1] == "hostchans":
                        self.cmd_trace_hostchans(command.split()[2])
                    elif command.split()[1] == "nickchans":
                        self.cmd_trace_nickchans(command.split()[2])
                    elif command.split()[1] == "nick": # trace nick $nick
                        self.cmd_trace_nick(command.split()[2])
                    elif command.split()[1] == "host": # trace host $host
                        self.cmd_trace_host(command.split()[2])
                else:
                    self.PutModule("%s is not a valid command." % command)
            elif command.split()[0] == "info":
                self.cmd_info()
            elif command.split()[0] == "save":
                self.cmd_save()
            elif command.split()[0] == "config":
                self.cmd_config(command.split()[1], command.split()[2])
            elif command.split()[0] == "add":
                self.cmd_add(command.split()[1], command.split()[2])
            elif command.split()[0] == "help":
                self.cmd_help()
            elif command.split()[0] == "merge":
                cmds = ["hosts", "chans"]
                if command.split()[1] in cmds:
                    if command.split()[1] == "hosts":
                        self.cmd_merge_hosts(command.split()[2])
                    elif command.split()[1] == "chans":
                        self.cmd_merge_chans(command.split()[2])
                else:
                    self.PutModule("%s is not a valid command." % command)
            elif command.split()[0] == "version":
                self.cmd_version()
            elif command.split()[0] == "stats":
                self.cmd_stats()
        else:
            self.PutModule("%s is not a valid command." % command)

    def save(self):
        if CONFIG.get("TEMP_FILES", False):
            # Save hosts
            with open(self.MODFOLDER + self.NETWORK + "_hosts.json.temp", 'w') as f:
                f.write(json.dumps(self.hosts, sort_keys=True, indent=4))
            # Save channels
            with open(self.MODFOLDER + self.NETWORK + "_chans.json.temp", 'w') as f:
                f.write(json.dumps(self.channels, sort_keys=True, indent=4))
            # Save config
            with open(self.MODFOLDER + "config.json", 'w') as f:
                f.write(json.dumps(CONFIG, sort_keys=True, indent=4))
            os.rename(self.MODFOLDER + self.NETWORK + "_hosts.json.temp",
                      self.MODFOLDER + self.NETWORK + "_hosts.json")
            os.rename(self.MODFOLDER + self.NETWORK + "_chans.json.temp",
                      self.MODFOLDER + self.NETWORK + "_chans.json")
            os.rename(self.MODFOLDER + "config.json.temp", self.MODFOLDER + "config.json")
        else:
            with open(self.MODFOLDER + self.NETWORK + "_hosts.json", 'w') as f:
                f.write(json.dumps(self.hosts, sort_keys=True, indent=4))
            with open(self.MODFOLDER + self.NETWORK + "_chans.json", 'w') as f:
                f.write(json.dumps(self.channels, sort_keys=True, indent=4))
            with open(self.MODFOLDER + "config.json", 'w') as f:
                f.write(json.dumps(CONFIG, sort_keys=True, indent=4))

    def change_config(self, var_name, value):
        if var_name in CONFIG:
            if var_name == "SAVE_EVERY":
                if int(value) > 1:
                    CONFIG["SAVE_EVERY"] = int(value)
                    self.timer.Stop()
                    self.timer.Start(CONFIG["SAVE_EVERY"])
                    self.PutModule("%s => %s" % (var_name, str(value)))
                else:
                    self.PutModule("Please use an int value larger than 0")
            elif var_name == "DEBUG_MODE":
                if int(value) in [0, 1]:
                    if int(value) == 0:
                        CONFIG["DEBUG_MODE"] = False
                        self.PutModule("Debug mode: OFF")
                    elif int(value) == 1:
                        CONFIG["DEBUG_MODE"] = True
                        self.PutModule("Debug mode: ON")
                else:
                    self.PutModule("valid values: 0, 1")
            elif var_name == "TEMP_FILES":
                if int(value) in [0, 1]:
                    if int(value) == 0:
                        CONFIG["TEMP_FILES"] = False
                        self.PutModule("Temp Files: OFF")
                    elif int(value) == 1:
                        CONFIG["TEMP_FILES"] = True
                        self.PutModule("Temp Files: ON")
                else:
                    self.PutModule("valid values: 0, 1")
            else:
                self.PutModule("%s is not a valid var." % var_name)
        self.save()

    def cmd_help(self):
        self.PutModule("nick <nick>")
        self.PutModule("sharedchans <nick1> <nick2> ... <nick#> | Show common channels between a list of users")
        self.PutModule("intersect <#channel1> <#channel2> ... <#channel#> | Display users common to a list of channels")
        self.PutModule("hostchans <host> | Get all channels a host has been seen in")
        self.PutModule("add <nick> <host> | Manually add a nick/host entry to the database")
        self.PutModule("save | Manually save the latest tracks to disk")
        self.PutModule("merge hosts <url> | Merges the hosts files from two users")
        self.PutModule("merge chans <url> |Merges the chans files from two users")
        self.PutModule("config <variable> <value> | Set configuration variables")
        self.PutModule("help | Print help from the module")
        self.PutModule("stats | Print nick and host stats for the network")
