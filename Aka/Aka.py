# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
#   Authors: AwwCookies (Aww), MuffinMedic (Evan)                     #
#   Last Update: Oct 16th 2015                                        #
#   Version: 1.5.3                                               # # #
#   Desc: A ZNC Module to track nicks                             # #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

import znc
import os
import json
import socket
import itertools
import datetime
import urllib.request
import shutil
import re

import requests

DEFAULT_CONFIG = {
    "SAVE_EVERY": 60 * 5, # 5 mins
    "TEMP_FILES": False, # 0/1
    "DEBUG_MODE": False, # 0/1
    "NOTIFY_ON_JOIN": False, # 0/1
    "NOTIFY_ON_JOIN_TIMEOUT": 300, # Seconds
    "NOTIFY_DEFAULT_MODE": "host" # host/nick
}

class SaveTimer(znc.Timer):
    def RunJob(self):
        self.GetModule().save()

class Aka(znc.Module):
    description = "Tracks nicks and hosts, allowing tracing and history viewing"
    wiki_page = "Aka"

    def OnLoad(self, args, message):

        self.USER = self.GetUser().GetUserName()
        self.NETWORK = self.GetNetwork().GetName()

        ''' Copy old data files to new ones '''
        self.old_MODFOLDER = znc.CUser(self.USER).GetUserPath() + "/moddata/Aka/"

        if os.path.exists(self.old_MODFOLDER + "config.json") and not os.path.exists(self.GetSavePath() + "/hosts.json"):
            shutil.copyfile(self.old_MODFOLDER + "config.json", self.GetSavePath() + "/config.json")
            # os.remove(self.old_MODFOLDER + "CONFIG[self.NETWORK].json")
        if os.path.exists(self.old_MODFOLDER + self.NETWORK + "_hosts.json"):
            shutil.copyfile(self.old_MODFOLDER + self.NETWORK + "_hosts.json", self.GetSavePath() + "/hosts.json")
            os.remove(self.old_MODFOLDER + self.NETWORK + "_hosts.json")
        if os.path.exists(self.old_MODFOLDER + self.NETWORK + "_chans.json"):
            shutil.copyfile(self.old_MODFOLDER + self.NETWORK + "_chans.json", self.GetSavePath() + "/chans.json")
            os.remove(self.old_MODFOLDER + self.NETWORK + "_chans.json")

        global CONFIG
        CONFIG = {}

        if os.path.exists(self.GetSavePath() + "/config.json"):
            CONFIG[self.NETWORK] = json.loads(open(self.GetSavePath() + "/config.json").read())
            for default in DEFAULT_CONFIG:
                if default not in CONFIG[self.NETWORK]:
                    CONFIG[self.NETWORK][default] = DEFAULT_CONFIG[default]
        else:
            with open(self.GetSavePath() + "/config.json", 'w') as f:
                f.write(json.dumps(DEFAULT_CONFIG, sort_keys=True, indent=4))
            CONFIG[self.NETWORK] = json.loads(open(self.GetSavePath() + "/config.json").read())

        self.hosts = {}
        if not os.path.exists(self.GetSavePath() + "/hosts.json"):
            with open(self.GetSavePath() + "/hosts.json", 'w') as f:
                f.write(json.dumps(self.hosts))
        else:
            self.hosts = json.loads(open(self.GetSavePath() + "/hosts.json", 'r').read())

        self.channels = {}
        if not os.path.exists(self.GetSavePath() + "/chans.json"):
            with open(self.GetSavePath() + "/chans.json", 'w') as f:
                f.write(json.dumps(self.channels))
        else:
            self.channels = json.loads(open(self.GetSavePath() + "/chans.json", 'r').read())

        # Do some checks
        if not os.path.exists(self.GetSavePath()):
            self.PutModule("Missing MODFOLDER")
            return False
        if not os.path.exists(self.GetSavePath() + "/config.json"):
            self.PutModule("Missing CONFIG file")
            return False
        if not os.path.exists(self.GetSavePath() + "/hosts.json"):
            self.PutModule("%shosts.json file was not created" % self.NETWORK)
            return False
        if not os.path.exists(self.GetSavePath() + "/chans.json"):
            self.PutModule("%shosts.json file was not created" % self.NETWORK)
            return False

        self.timer = self.CreateTimer(SaveTimer)
        self.timer.Start(CONFIG[self.NETWORK].get("SAVE_EVERY", 60 * 5))

        if CONFIG[self.NETWORK].get("NOTIFY_ON_JOIN", True):
            global TIMEOUTS
            TIMEOUTS = {}

        # If there was no problems setting up then load the script
        return True

    def process(self, host, nick):
        if CONFIG[self.NETWORK].get("DEBUG_MODE", False):
            self.PutModule("DEBUG: Adding %s => %s" % (nick, host))
        if host not in self.hosts:
            self.hosts[host] = []
            self.hosts[host].append(nick)
        else:
            if nick not in self.hosts[host]:
                self.hosts[host].append(nick)

    def process_chan(self, host, nick, channel):
        if CONFIG[self.NETWORK].get("DEBUG_MODE", False):
            self.PutModule("DEBUG: Adding %s => (%s, %s)" % (channel, nick, host))
        if channel not in self.channels:
            self.channels[channel] = []
            self.channels[channel].append((nick, host))
        else:
            if (nick, host) not in self.channels[channel]:
                self.channels[channel].append((nick, host))

    def OnRaw(self, message):
        global get_raw_geoip_host
        if get_raw_geoip_host:
            get_raw_geoip_host = False
            self.geoip_process(str(message.s).split()[5])
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
        ''' TO ADD
        Place in channel instead of PM
        self.PutUser(":*Aka!Aka@znc.in PRIVMSG " + channel.GetName() + " :" + str(user.GetNick()) + " has joined")
        '''
        self.process(user.GetHost(), user.GetNick())
        self.process_chan(user.GetHost(), user.GetNick(), channel.GetName())
        if CONFIG[self.NETWORK].get("NOTIFY_ON_JOIN", True) and user.GetNick() != self.GetUser().GetNick():
            if user.GetNick() in TIMEOUTS:
                diff = datetime.datetime.now() - TIMEOUTS[user.GetNick()]
                if diff.total_seconds() > CONFIG[self.NETWORK]["NOTIFY_ON_JOIN_TIMEOUT"]:
                    self.PutModule(user.GetNick() + " (" + user.GetHost() + ")" + " has joined " + channel.GetName())
                    if CONFIG[self.NETWORK]["NOTIFY_DEFAULT_MODE"] == "nick":
                        self.cmd_trace_nick(user.GetNick())
                    elif CONFIG[self.NETWORK]["NOTIFY_DEFAULT_MODE"] == "host":
                        self.cmd_trace_host(user.GetHost())
                    TIMEOUTS[user.GetNick()] = datetime.datetime.now()
            else:
                self.PutModule(user.GetNick() + " (" + user.GetHost() + ")" + " has joined " + channel.GetName())
                if CONFIG[self.NETWORK]["NOTIFY_DEFAULT_MODE"] == "nick":
                    self.cmd_trace_nick(user.GetNick())
                elif CONFIG[self.NETWORK]["NOTIFY_DEFAULT_MODE"] == "host":
                    self.cmd_trace_host(user.GetHost())
                TIMEOUTS[user.GetNick()] = datetime.datetime.now()

    def OnNick(self, user, new_nick, channels):
        self.process(user.GetHost(), new_nick)
        for chan in channels:
            self.process_chan(user.GetHost(), user.GetNick(), chan.GetName())

    def OnPart(self, user, channel, message):
        self.process(user.GetHost(), user.GetNick())
        self.process_chan(user.GetHost(), user.GetNick(), channel.GetName())

    def OnQuit(self, user, message, channels):
        self.process(user.GetHost(), user.GetNick())
        for chan in channels:
            self.process_chan(user.GetHost(), user.GetNick(), chan.GetName())

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
            self.PutModule("%s was found in: %s" % (host, ' '.join(sorted(set(found), key=str.lower))))
        else:
            self.PutModule("%s was not found in any channels." % (host))

    def cmd_trace_nickchans(self, nick):
        found = []
        for chan in self.channels:
            for user in self.channels[chan]:
                if nick.lower() == user[0].lower():
                    found.append(chan)
        if found:
            self.PutModule("%s was found in: %s" % (nick, ' '.join(sorted(set(found), key=str.lower))))
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

    def cmd_geoip(self, method, user):
        global get_raw_geoip_host
        if method == "host":
            self.geoip_process(user)
        elif method == "nick":
            get_raw_geoip_host = True
            self.PutIRC("WHO " + user)

    def geoip_process(self, user):
        ipv4 = '(?:[0-9]{1,3}(\.|\-)){3}[0-9]{1,3}'
        ipv6 = '^((?:[0-9A-Fa-f]{1,4}))((?::[0-9A-Fa-f]{1,4}))*::((?:[0-9A-Fa-f]{1,4}))((?::[0-9A-Fa-f]{1,4}))*|((?:[0-9A-Fa-f]{1,4}))((?::[0-9A-Fa-f]{1,4})){7}$'
        rdns = '^(([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]*[a-zA-Z0-9])\.)*([A-Za-z0-9]|[A-Za-z0-9][A-Za-z0-9\-]*[A-Za-z0-9])$'

        if (re.search(ipv6, str(user)) or re.search(ipv4, str(user)) or re.search(rdns, str(user))) and user != "of":
            if re.search(ipv4, str(user)):
                ip = re.sub('[^\w.]',".",((re.search(ipv4, str(user))).group(0)))
            elif re.search(ipv6, str(user)) or re.search(rdns, str(user)):
                ip = str(user)
            url = 'http://ip-api.com/json/' + ip + '?fields=country,regionName,city,lat,lon,timezone,mobile,proxy,query,reverse,status'
            loc = requests.get(url)
            loc_json = loc.json()
            if loc_json["status"] != "fail":
                self.PutModule(user + " is located in " + loc_json["city"] + ", " + loc_json["regionName"] + ", " + loc_json["country"] + " (" + str(loc_json["lat"]) + ", " + str(loc_json["lon"]) + " ) / Timezone: " + loc_json["timezone"] + " / Proxy: " + str(loc_json["proxy"]) + " / Mobile: " + str(loc_json["mobile"]) + " / IP: " + loc_json["query"] + " " + loc_json["reverse"])
            else:
                self.PutModule("Unable to geolocate " + user)
        elif user == "of":
            self.PutModule("User does not exist.")
        else:
            self.PutModule("Invalid host for geolocation (" + user + ")")

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
        Consolidates two *hosts.json files
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
        Consolidates two *chans.json files
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
        self.PutModule("Aka nick tracking module by AwwCookies (Aww) and MuffinMedic (Evan) - http://wiki.znc.in/Aka")

    def cmd_stats(self):
        nicks = 0
        for host in self.hosts:
            nicks += len(self.hosts[host])
        self.PutModule("Nicks: %s" % "{:,}".format(nicks))
        self.PutModule("Hosts: %s" % "{:,}".format(len(self.hosts)))

    def OnModCommand(self, command):
        # Valid Commands
        cmds = ["trace", "geoip", "help", "config", "info", "save", "add", "merge", "version", "stats", "update"]
        if command.split()[0] in cmds:
            if command.split()[0] == "trace":
                cmds = ["sharedchans", "intersect", "hostchans", "nickchans", "nick", "host", "geoip"]
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
            elif command.split()[0] == "geoip":
                cmds = ["host", "nick"]
                if command.split()[1] in cmds:
                    self.cmd_geoip(command.split()[1], command.split()[2])
                else:
                    self.PutModule(command.split()[0] + " " + command.split()[1] + " is not a valid command.")
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
            elif command.split()[0] == "update":
                self.update()
        else:
            self.PutModule("%s is not a valid command." % command)

    def save(self):
        if CONFIG[self.NETWORK].get("TEMP_FILES", False):
            # Save hosts
            with open(self.GetSavePath() + "hosts.json.temp", 'w') as f:
                f.write(json.dumps(self.hosts, sort_keys=True, indent=4))
            # Save channels
            with open(self.GetSavePath() + "chans.json.temp", 'w') as f:
                f.write(json.dumps(self.channels, sort_keys=True, indent=4))
            # Save CONFIG
            with open(self.GetSavePath() + "/config.json", 'w') as f:
                f.write(json.dumps(CONFIG[self.NETWORK], sort_keys=True, indent=4))
            os.rename(self.GetSavePath() + "hosts.json.temp",
                      self.GetSavePath() + "/hosts.json")
            os.rename(self.GetSavePath() + "chans.json.temp",
                      self.GetSavePath() + "/chans.json")
            os.rename(self.GetSavePath() + "config.json.temp", self.GetSavePath() + "/config.json")
        else:
            with open(self.GetSavePath() + "/hosts.json", 'w') as f:
                f.write(json.dumps(self.hosts, sort_keys=True, indent=4))
            with open(self.GetSavePath() + "/chans.json", 'w') as f:
                f.write(json.dumps(self.channels, sort_keys=True, indent=4))
            with open(self.GetSavePath() + "/config.json", 'w') as f:
                f.write(json.dumps(CONFIG[self.NETWORK], sort_keys=True, indent=4))

    def change_config(self, var_name, value):
        if var_name in CONFIG[self.NETWORK]:
            if var_name == "SAVE_EVERY":
                if int(value) >= 1:
                    CONFIG[self.NETWORK]["SAVE_EVERY"] = int(value)
                    self.timer.Stop()
                    self.timer.Start(CONFIG[self.NETWORK]["SAVE_EVERY"])
                    self.PutModule("%s => %s" % (var_name, str(value)))
                else:
                    self.PutModule("Please use an int value larger than 0")
            elif var_name == "DEBUG_MODE":
                if int(value) in [0, 1]:
                    if int(value) == 0:
                        CONFIG[self.NETWORK]["DEBUG_MODE"] = False
                        self.PutModule("Debug mode: OFF")
                    elif int(value) == 1:
                        CONFIG[self.NETWORK]["DEBUG_MODE"] = True
                        self.PutModule("Debug mode: ON")
                else:
                    self.PutModule("valid values: 0, 1")
            elif var_name == "TEMP_FILES":
                if int(value) in [0, 1]:
                    if int(value) == 0:
                        CONFIG[self.NETWORK]["TEMP_FILES"] = False
                        self.PutModule("Temp Files: OFF")
                    elif int(value) == 1:
                        CONFIG[self.NETWORK]["TEMP_FILES"] = True
                        self.PutModule("Temp Files: ON")
                else:
                    self.PutModule("Valid values: 0, 1")
            elif var_name == "NOTIFY_ON_JOIN":
                if int(value) in [0, 1]:
                    if int(value) == 0:
                        CONFIG[self.NETWORK]["NOTIFY_ON_JOIN"] = False
                        self.PutModule("Notify On Join: OFF")
                    elif int(value) == 1:
                        CONFIG[self.NETWORK]["NOTIFY_ON_JOIN"] = True
                        self.PutModule("Notify On Join: ON")
                else:
                    self.PutModule("Valid values: 0, 1")
            elif var_name == "NOTIFY_ON_JOIN_TIMEOUT":
                if int(value) >= 1:
                    CONFIG[self.NETWORK]["NOTIFY_ON_JOIN_TIMEOUT"] = int(value)
                    self.timer.Stop()
                    self.timer.Start(CONFIG[self.NETWORK]["NOTIFY_ON_JOIN_TIMEOUT"])
                    self.PutModule("%s => %s" % (var_name, str(value)))
                else:
                    self.PutModule("Please use an int value larger than 0")
            elif var_name == "NOTIFY_DEFAULT_MODE":
                if str(value) in ["nick", "host"]:
                    if str(value) == "nick":
                        CONFIG[self.NETWORK]["NOTIFY_DEFAULT_MODE"] = "nick"
                        self.PutModule("Notify Mode: NICK")
                    elif str(value) == "host":
                        CONFIG[self.NETWORK]["NOTIFY_DEFAULT_MODE"] = "host"
                        self.PutModule("Notify Mode: HOST")
                else:
                    self.PutModule("Valid values: nick, host")
            else:
                self.PutModule("%s is not a valid var." % var_name)
        self.save()

    def update(self):
        if self.GetUser().IsAdmin():
            new_version = urllib.request.urlopen("https://raw.githubusercontent.com/AwwCookies/ZNC-Modules/master/Aka/Aka.py")
            with open(self.GetModPath(), 'w') as f:
                f.write(new_version.read().decode('utf-8'))
                self.PutModule("Aka successfully updated.")
                znc.CModule().UpdateModule('Aka')
        else:
            self.PutModule("You must be an administrator to update this module.")

    def cmd_help(self):
        self.PutModule("+====================+===========================================+======================================================+")
        self.PutModule("| Command            | Arguments                                 | Description                                          |")
        self.PutModule("+=====================+==========================================+======================================================+")
        self.PutModule("| trace nick         | <nick>                                    | Shows nick change and host history for given nick")
        self.PutModule("+--------------------+-------------------------------------------+------------------------------------------------------+")
        self.PutModule("| trace sharedchans  | <nick1> <nick2> ... <nick#>               | Show common channels between a list of users")
        self.PutModule("+--------------------+-------------------------------------------+------------------------------------------------------+")
        self.PutModule("| trace intersect    | <#channel1> <#channel2> ... <#channel#>   | Display users common to a list of channels")
        self.PutModule("+--------------------+-------------------------------------------+------------------------------------------------------+")
        self.PutModule("| trace nickchans    | <nick>                                    | Get all channels a nick has been seen in")
        self.PutModule("+--------------------+-------------------------------------------+------------------------------------------------------+")
        self.PutModule("| geoip host         | <host>                                    | Geolocates host")
        self.PutModule("+--------------------+-------------------------------------------+------------------------------------------------------+")
        self.PutModule("| geoip nick         | <nick>                                    | Geolocates host by nick")
        self.PutModule("+--------------------+-------------------------------------------+------------------------------------------------------+")
        self.PutModule("| add                | <nick> <host>                             | Manually add a nick/host entry to the database")
        self.PutModule("+--------------------+-------------------------------------------+------------------------------------------------------+")
        self.PutModule("| merge hosts        | <url>                                     | Merges the hosts files from two users")
        self.PutModule("+--------------------+-------------------------------------------+------------------------------------------------------+")
        self.PutModule("| merge chans        | <url>                                     | Merges the chans files from two users")
        self.PutModule("+--------------------+-------------------------------------------+------------------------------------------------------+")
        self.PutModule("| config             | <variable> <value>                        | Set configururation variables per network (See README)")
        self.PutModule("+--------------------+-------------------------------------------+------------------------------------------------------+")
        self.PutModule("| save               |                                           | Manually save the latest tracks to disk")
        self.PutModule("+--------------------+-------------------------------------------+------------------------------------------------------+")
        self.PutModule("| stats              |                                           | Print nick and host stats for the network")
        self.PutModule("+--------------------+-------------------------------------------+------------------------------------------------------+")
        self.PutModule("| update             |                                           | Updates Aka to latest version")
        self.PutModule("+--------------------+-------------------------------------------+------------------------------------------------------+")
        self.PutModule("| help               |                                           | Print help from the module")
        self.PutModule("+====================+===========================================+======================================================+")
