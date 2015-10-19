# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
#   Authors: AwwCookies (Aww), MuffinMedic (Evan)                     #
#   Last Update: Oct 19th 2015                                        #
#   Version: 1.6.1                                               # # #
#   Desc: A ZNC Module to track nicks                             # #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

import znc
import os
import socket
import itertools
import datetime
import urllib.request
import shutil
import re
import sqlite3
import json

import requests

''' NO RESULTS OUTPUT '''

DEFAULT_CONFIG = {
    "DEBUG_MODE": False, # 0/1
    "NOTIFY_ON_JOIN": False, # 0/1
    "NOTIFY_ON_JOIN_TIMEOUT": 300, # Seconds
    "NOTIFY_DEFAULT_MODE": "host", # host/nick
    "NOTIFY_ON_MODE": 0 # 0/1
}

class aka(znc.Module):
    module_types = [znc.CModInfo.NetworkModule]
    description = "Tracks nicks and hosts, allowing tracing and history viewing"
    wiki_page = "aka"

    ''' OK '''
    def OnLoad(self, args, message):

        self.get_raw_geoip_host = False
        self.TIMEOUTS = {}
        self.CONFIG = {}

        self.USER = self.GetUser().GetUserName()
        self.NETWORK = self.GetNetwork().GetName()

        self.transfer_data()

        return True

    ''' OK '''
    def process_new(self, host, nick, channel, message, auto):
        if self.CONFIG.get("DEBUG_MODE", False):
            self.PutModule("DEBUG: Adding %s => %s" % (nick, host))

        query = "SELECT seen FROM users WHERE LOWER(nick) = '" + nick.lower() + "' AND LOWER(host) = '" + host.lower() + "'  AND LOWER(channel) = '" + channel.lower() + "'"

        self.c.execute(query)
        data = self.c.fetchall()
        if len(data) == 0:
            if auto == True:
                query = "INSERT INTO users (host, nick, channel) VALUES ('" + host + "','" + nick + "','" + channel + "')"
            else:
                query = "INSERT INTO users VALUES ('" + host + "','" + nick + "','" + channel + "','" + str(datetime.datetime.now()) + "','" + str(message) + "')"
            self.c.execute(query)

        else:
            if auto == False:
                query = "UPDATE users SET seen = '" + str(datetime.datetime.now()) + "', message = '" + str(message) + "' WHERE LOWER(nick) = '" + nick.lower() + "' AND LOWER(host) = '" + host.lower() + "'  AND LOWER(channel) = '" + channel.lower() + "'"
            self.c.execute(query)
        self.conn.commit()

    ''' OK '''
    def OnRaw(self, message):
        if self.get_raw_geoip_host:
            self.get_raw_geoip_host = False
            self.geoip_process(str(message.s).split()[5], str(message.s).split()[7])
        if str(message.s).split()[1] == "352": # on WHO
            host = str(message.s).split()[5]
            nick = str(message.s).split()[7]
            channel = str(message.s).split()[3]
            self.process_new(host, nick, channel, True)
        elif str(message.s).split()[1] == "311": # on WHOIS
            host = str(message.s).split()[5]
            nick = str(message.s).split()[3]
            channel = str(message.s).split()[6]
            self.process_new(host, nick, channel, True)
        elif str(message.s).split()[1] == "314": # on WHOWAS
            host = str(message.s).split()[5]
            nick = str(message.s).split()[3]
            self.process_new(host, nick, channel, True)

    ''' OK '''
    def OnJoin(self, user, channel):
        self.process_new(user.GetHost(), user.GetNick(), channel.GetName(), True)

        if self.CONFIG.get("NOTIFY_ON_JOIN", True) and user.GetNick() != self.GetUser().GetNick():
            if user.GetNick() in self.TIMEOUTS:
                diff = datetime.datetime.now() - self.TIMEOUTS[user.GetNick()]
                if diff.total_seconds() > self.CONFIG["NOTIFY_ON_JOIN_TIMEOUT"]:
                    self.PutModule(user.GetNick() + " (" + user.GetHost() + ")" + " has joined " + channel.GetName())
                    if self.CONFIG["NOTIFY_DEFAULT_MODE"] == "nick":
                        self.cmd_trace_nick(user.GetNick())
                    elif self.CONFIG["NOTIFY_DEFAULT_MODE"] == "host":
                        self.cmd_trace_host(user.GetHost())
                    self.TIMEOUTS[user.GetNick()] = datetime.datetime.now()
            else:
                self.PutModule(user.GetNick() + " (" + user.GetHost() + ")" + " has joined " + channel.GetName())
                if self.CONFIG["NOTIFY_DEFAULT_MODE"] == "nick":
                    self.cmd_trace_nick(user.GetNick())
                elif self.CONFIG["NOTIFY_DEFAULT_MODE"] == "host":
                    self.cmd_trace_host(user.GetHost())
                self.TIMEOUTS[user.GetNick()] = datetime.datetime.now()

    ''' OK '''
    def OnNick(self, user, new_nick, channels):
        for chan in channels:
            self.process_new(user.GetHost(), new_nick, chan.GetName(), None, True)

    ''' OK '''
    def OnChanMsg(self, user, channel, message):
        self.process_new(user.GetHost(), user.GetNick(), channel.GetName(), message, False)

    ''' OK '''
    def OnPart(self, user, channel, message):
        self.process_new(user.GetHost(), user.GetNick(), channel.GetName(), None, True)

    ''' OK '''
    def OnQuit(self, user, message, channels):
        for chan in channels:
            self.process_new(user.GetHost(), user.GetNick(), chan.GetName(), None, True)

    ''' OK '''
    def OnMode(self, op, channel, mode, arg, added, nochange):
        if self.CONFIG.get("NOTIFY_ON_MODE", True):
            if mode == 79:
                mode = 'O'
            elif mode == 111:
                mode = 'o'
            elif mode == 98:
                mode = 'b'
            elif mode == 118:
                mode = 'v'
            elif mode == 113:
                mode = 'q'
            elif mode == 115:
                mode = 's'
            elif mode == 112:
                mode = 'p'
            elif mode == 107:
                mode = 'k'
            elif mode == 97:
                mode = 'a'
            elif mode == 109:
                mode = 'm'
            elif mode == 110:
                mode = 'n'
            elif mode == 108:
                mode = 'l'
            elif mode == 101:
                mode = 'e'
            elif mode == 105:
                mode = 'i'
            elif mode == 114:
                mode = 'r'
            elif mode == 73:
                mode = 'l'
            elif mode == 116:
                mode = 't'
            elif mode == 104:
                mode = 'h'
            if added:
                self.PutModule(str(op) + " has set mode +" + str(mode) + " " + str(arg) + " in " + str(channel))
            else:
                self.PutModule(str(op) + " has set mode -" + str(mode) + " " + str(arg) + " in " + str(channel))

    ''' OK '''
    def cmd_trace_nick(self, nick):
        query = "SELECT host, nick FROM users WHERE LOWER(nick) = '" + str(nick).lower() + "' GROUP BY host ORDER BY host"
        self.c.execute(query)
        c2 = self.conn.cursor()
        for row in self.c:
            out = str(nick) + " was also known as: "
            query = "SELECT host, nick FROM users WHERE LOWER(host) = '" + str(row[0]).lower() + "' GROUP BY nick ORDER BY nick COLLATE NOCASE"
            c2.execute(query)
            for row2 in c2:
                out += row2[1] + ", "
            out = out[:-2]
            out += " (" + str(row[0]) + ")"
            self.PutModule(out)

    ''' OK '''
    def cmd_trace_host(self, host):
        query = "SELECT nick, host FROM users WHERE LOWER(host) = '" + str(host).lower() + "' GROUP BY nick ORDER BY nick COLLATE NOCASE"
        self.c.execute(query)
        out = str(host) + " was known as: "
        for row in self.c:
            out += row[0] + ", "
        out = out[:-2]
        self.PutModule(out)

    ''' OK '''
    def cmd_trace_nickchans(self, nick):
        query = "SELECT DISTINCT channel FROM users WHERE LOWER(nick)  = '" + str(nick).lower() + "' AND channel IS NOT NULL ORDER BY channel"
        out = str(nick) + " was found in:"
        self.c.execute(query)
        for chan in self.c:
            out += " " + chan[0]
        self.PutModule(out)

    ''' OK '''
    def cmd_trace_hostchans(self, host):
        query = "SELECT DISTINCT channel FROM users WHERE LOWER(host)  = '" + str(host).lower() + "' AND channel IS NOT NULL ORDER BY channel"
        out = str(host) + " was found in:"
        self.c.execute(query)
        for chan in self.c:
            out += " " + chan[0]
        self.PutModule(out)

    ''' OK '''
    def cmd_trace_sharedchans(self, nicks):
        nick_list = ''
        query = "SELECT DISTINCT channel FROM users WHERE ("
        for nick in nicks:
            query += "LOWER(nick) = '" + str(nick).lower() + "' OR "
            nick_list += " " + nick
        query = query[:-5]
        query += "') AND channel IS NOT NULL GROUP BY channel HAVING COUNT(DISTINCT nick) = " + str(len(nicks))  + " ORDER BY channel COLLATE NOCASE"

        out = "Common channels between" + nick_list + ": "
        self.c.execute(query)
        for chan in self.c:
            out += chan[0] + " "
        self.PutModule(out)

    ''' OK '''
    def cmd_trace_intersect(self, chans):
        chan_list = ''
        query = "SELECT DISTINCT nick FROM users WHERE "
        for chan in chans:
            query += "LOWER(channel) = '" + str(chan).lower() + "' OR "
            chan_list += " " + chan
        query = query[:-5]
        query += "' GROUP BY nick HAVING COUNT(DISTINCT channel) = " + str(len(chans))  + " ORDER BY nick COLLATE NOCASE"

        out = "Shared users between" + chan_list + ": "
        self.c.execute(query)
        for nick in self.c:
            out += nick[0] + " "
        self.PutModule(out)

    ''' OK '''
    def cmd_seen(self, mode, channel, nick):
        if mode == "in":
            query = "SELECT seen, message FROM users WHERE seen = (SELECT MAX(seen) FROM users WHERE LOWER(nick) = '" + str(nick).lower() + "' AND LOWER(channel) = '" + str(channel).lower() + "') AND LOWER(nick) = '" + str(nick).lower() + "' AND LOWER(channel) = '" + str(channel).lower() + "'"
            self.c.execute(query)
            for row in self.c:
                self.PutModule(str(nick) + " was last seen in " + str(channel) + " at " + str(row[0]) + " saying \"" + str(row[1]) + "\"")
        elif mode == "nick":
            query = "SELECT channel, MAX(seen), message FROM users WHERE seen = (SELECT MAX(seen) FROM users WHERE LOWER(nick) = '" + str(nick).lower() + "') AND LOWER(nick) = '" + str(nick).lower() + "'"
            self.c.execute(query)
            for row in self.c:
                self.PutModule(str(nick) + " was last seen in " + str(row[0]) + " at " + str(row[1]) + " saying \"" + str(row[2]) + "\"")

    ''' OK '''
    def cmd_geoip(self, method, user):
        if method == "host":
            self.geoip_process(user, user)
        elif method == "nick":
            self.get_raw_geoip_host = True
            self.PutIRC("WHO " + user)

    ''' OK '''
    def geoip_process(self, host, nick):
        ipv4 = '(?:[0-9]{1,3}(\.|\-)){3}[0-9]{1,3}'
        ipv6 = '^((?:[0-9A-Fa-f]{1,4}))((?::[0-9A-Fa-f]{1,4}))*::((?:[0-9A-Fa-f]{1,4}))((?::[0-9A-Fa-f]{1,4}))*|((?:[0-9A-Fa-f]{1,4}))((?::[0-9A-Fa-f]{1,4})){7}$'
        rdns = '^(([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]*[a-zA-Z0-9])\.)*([A-Za-z0-9]|[A-Za-z0-9][A-Za-z0-9\-]*[A-Za-z0-9])$'

        if (re.search(ipv6, str(host)) or re.search(ipv4, str(host)) or re.search(rdns, str(host))) and host != "of":
            if re.search(ipv4, str(host)):
                ip = re.sub('[^\w.]',".",((re.search(ipv4, str(host))).group(0)))
            elif re.search(ipv6, str(host)) or re.search(rdns, str(host)):
                ip = str(host)
            url = 'http://ip-api.com/json/' + ip + '?fields=country,regionName,city,lat,lon,timezone,mobile,proxy,query,reverse,status,message'
            loc = requests.get(url)
            loc_json = loc.json()
            if loc_json["status"] != "fail":
                self.PutModule(nick + " is located in " + loc_json["city"] + ", " + loc_json["regionName"] + ", " + loc_json["country"] + " (" + str(loc_json["lat"]) + ", " + str(loc_json["lon"]) + ") / Timezone: " + loc_json["timezone"] + " / Proxy: " + str(loc_json["proxy"]) + " / Mobile: " + str(loc_json["mobile"]) + " / IP: " + loc_json["query"] + " " + loc_json["reverse"])
            else:
                self.PutModule("Unable to geolocate " + host + ". (Reason: " + loc_json["message"] + ")")
        elif host == "of":
            self.PutModule("User does not exist.")
        else:
            self.PutModule("Invalid host for geolocation (" + host + ")")

    ''' OK '''
    def cmd_config(self, var_name, value):
        self.change_config(var_name, value)

    ''' OK'''
    def cmd_getconfig(self):
        self.PutModule(str(self.CONFIG))

    ''' OK '''
    def cmd_add(self, nick, host, channel):
        self.process_new(host, nick, channel, False)
        self.PutModule("%s => %s" % (nick, host, channel))

    ''' FIX '''
    '''
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
    '''

    ''' FIX '''
    '''
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
    '''

    ''' OK '''
    def cmd_info(self):
        self.PutModule("aka nick tracking module by AwwCookies (Aww) and MuffinMedic (Evan) - http://wiki.znc.in/aka")

    ''' OK '''
    def cmd_version(self):
        """
        Pull the version number from line 4 of this script
        """
        self.PutModule(open(__file__, 'r').readlines()[3].replace("#", "").strip())

    ''' OK '''
    def cmd_stats(self):
        self.c.execute('SELECT COUNT(DISTINCT host), COUNT(DISTINCT nick) FROM users')
        for row in self.c:
            self.PutModule("Nicks: " + str(row[1]))
            self.PutModule("Hosts: " + str(row[0]))

    ''' OK '''
    def OnModCommand(self, command):
        # Valid Commands
        cmds = ["trace", "seen", "geoip", "help", "config", "getconfig", "info", "add", "merge", "version", "stats", "update"]
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
            elif command.split()[0] == "seen":
                cmds = ["in", "nick"]
                if command.split()[1] in cmds:
                    if command.split()[1] == "nick":
                        self.cmd_seen(command.split()[1], None, command.split()[2])
                    elif command.split()[1] == "in":
                        self.cmd_seen(command.split()[1], command.split()[2], command.split()[3])
                else:
                    self.PutModule(command.split()[0] + " " + command.split()[1] + " is not a valid command.")
            elif command.split()[0] == "geoip":
                cmds = ["host", "nick"]
                if command.split()[1] in cmds:
                    self.cmd_geoip(command.split()[1], command.split()[2])
                else:
                    self.PutModule(command.split()[0] + " " + command.split()[1] + " is not a valid command.")
            elif command.split()[0] == "info":
                self.cmd_info()
            elif command.split()[0] == "config":
                self.cmd_config(command.split()[1], command.split()[2])
            elif command.split()[0] == "getconfig":
                self.cmd_getconfig()
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

    ''' OK '''
    def change_config(self, var_name, value):
        if var_name in self.CONFIG:
            if var_name == "DEBUG_MODE":
                if int(value) in [0, 1]:
                    if int(value) == 0:
                        self.CONFIG["DEBUG_MODE"] = False
                        self.PutModule("Debug mode: OFF")
                    elif int(value) == 1:
                        self.CONFIG["DEBUG_MODE"] = True
                        self.PutModule("Debug mode: ON")
                else:
                    self.PutModule("valid values: 0, 1")
            elif var_name == "NOTIFY_ON_JOIN":
                if int(value) in [0, 1]:
                    if int(value) == 0:
                        self.CONFIG["NOTIFY_ON_JOIN"] = False
                        self.PutModule("Notify On Join: OFF")
                    elif int(value) == 1:
                        self.CONFIG["NOTIFY_ON_JOIN"] = True
                        self.PutModule("Notify On Join: ON")
                else:
                    self.PutModule("Valid values: 0, 1")
            elif var_name == "NOTIFY_ON_JOIN_TIMEOUT":
                if int(value) >= 1:
                    self.CONFIG["NOTIFY_ON_JOIN_TIMEOUT"] = int(value)
                    self.timer.Stop()
                    self.timer.Start(self.CONFIG["NOTIFY_ON_JOIN_TIMEOUT"])
                    self.PutModule("%s => %s" % (var_name, str(value)))
                else:
                    self.PutModule("Please use an int value larger than 0")
            elif var_name == "NOTIFY_DEFAULT_MODE":
                if str(value) in ["nick", "host"]:
                    if str(value) == "nick":
                        self.CONFIG["NOTIFY_DEFAULT_MODE"] = "nick"
                        self.PutModule("Notify Mode: NICK")
                    elif str(value) == "host":
                        self.CONFIG["NOTIFY_DEFAULT_MODE"] = "host"
                        self.PutModule("Notify Mode: HOST")
                else:
                    self.PutModule("Valid values: nick, host")
            elif var_name == "NOTIFY_ON_MODE":
                if int(value) in [0, 1]:
                    if int(value) == 0:
                        self.CONFIG["NOTIFY_ON_MODE"] = False
                        self.PutModule("Notify On Mode: OFF")
                    elif int(value) == 1:
                        self.CONFIG["NOTIFY_ON_MODE"] = True
                        self.PutModule("Notify On Mode: ON")
                else:
                    self.PutModule("Valid values: 0, 1")
            else:
                self.PutModule("%s is not a valid var." % var_name)
        with open(self.GetSavePath() + "/config.json", 'w') as f:
            f.write(json.dumps(self.CONFIG, sort_keys=True, indent=4))

    ''' OK '''
    def update(self):
        if self.GetUser().IsAdmin():
            new_version = urllib.request.urlopen("https://raw.githubusercontent.com/AwwCookies/ZNC-Modules/sqlite/Aka/aka.py")
            with open(self.GetModPath(), 'w') as f:
                f.write(new_version.read().decode('utf-8'))
                self.PutModule("aka successfully updated.")
                znc.CModule().UpdateModule('aka')
        else:
            self.PutModule("You must be an administrator to update this module.")

    def db_setup(self):
        self.conn = sqlite3.connect(self.GetSavePath() + "/aka." + self.NETWORK + ".db")
        self.c = self.conn.cursor()
        self.c.execute("create table if not exists users (host, nick, channel, seen, UNIQUE(host COLLATE NOCASE, nick COLLATE NOCASE, channel COLLATE NOCASE))")

        ''' ADDITIONAL TABLES '''
        self.c.execute("PRAGMA table_info(users)")
        exists = False
        for table in self.c:
            if str(table[1]) == 'message':
                exists = True
        if exists == False:
            self.c.execute("ALTER TABLE users ADD COLUMN message")


    ''' OK '''
    def transfer_data(self):

        if os.path.exists(znc.CUser(self.USER).GetUserPath() + "/networks/" + self.NETWORK + "/moddata/Aka"):
            os.rename(znc.CUser(self.USER).GetUserPath() + "/networks/" + self.NETWORK + "/moddata/Aka", self.GetSavePath())

        self.db_setup()

        self.old_MODFOLDER = znc.CUser(self.USER).GetUserPath() + "/moddata/Aka/"

        if os.path.exists(self.old_MODFOLDER + "config.json") and not os.path.exists(self.GetSavePath() + "/hosts.json"):
            shutil.move(self.old_MODFOLDER + "config.json", self.GetSavePath() + "/config.json")
        if os.path.exists(self.old_MODFOLDER + self.NETWORK + "_hosts.json"):
            shutil.move(self.old_MODFOLDER + self.NETWORK + "_hosts.json", self.GetSavePath() + "/hosts.json")
        if os.path.exists(self.old_MODFOLDER + self.NETWORK + "_chans.json"):
            shutil.move(self.old_MODFOLDER + self.NETWORK + "_chans.json", self.GetSavePath() + "/chans.json")
        if os.path.exists(self.GetSavePath() + "/config.json"):
            self.CONFIG = json.loads(open(self.GetSavePath() + "/config.json").read())
            for default in DEFAULT_CONFIG:
                if default not in self.CONFIG:
                    self.CONFIG[default] = DEFAULT_CONFIG[default]
            new_config = {}
            for setting in self.CONFIG:
                if setting in DEFAULT_CONFIG:
                    new_config[setting] = self.CONFIG[setting]
            self.CONFIG = new_config
            with open(self.GetSavePath() + "/config.json", 'w') as f:
                f.write(json.dumps(new_config, sort_keys=True, indent=4))

        if os.path.exists(self.GetSavePath() + "/hosts.json") and os.path.exists (self.GetSavePath() + "/hosts.json"):

            self.PutModule("aka needs to migrate your data to the new database format. Your data has been backed up. This may take a few minutes and will only happen once.")

            chans = {}
            chans = json.loads(open(self.GetSavePath() + "/chans.json", 'r').read())

            for chan in chans:
                for user in chans[chan]:
                        query = "INSERT OR IGNORE INTO users (host, nick, channel) VALUES ('" + str(user[1]) + "','" + str(user[0]) + "','" + str(chan) + "')"
                        self.c.execute(query)
                del user
            del chans[chan]
            self.conn.commit()

            hosts = {}
            hosts = json.loads(open(self.GetSavePath() + "/hosts.json", 'r').read())
            for host in hosts:
                for nick in hosts[host]:
                        query = "INSERT OR IGNORE INTO users (host, nick) VALUES ('" + str(host) + "','" + str(nick) + "')"
                        self.c.execute(query)
                del nick
            del hosts[host]
            self.conn.commit()

            self.c.execute("VACUUM")

            shutil.move(self.GetSavePath() + "/hosts.json", self.GetSavePath() + "/hosts_processed.json")
            shutil.move(self.GetSavePath() + "/chans.json", self.GetSavePath() + "/chans_processed.json")

            self.PutModule("Data migration complete.")

    ''' OK '''
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
        self.PutModule("| seen nick          | <nick>                                    | Last time and where the nick was seen")
        self.PutModule("+--------------------+-------------------------------------------+------------------------------------------------------+")
        self.PutModule("| seen in            | <channel> <nick>                          | Last time and where the nick was seen")
        self.PutModule("+--------------------+-------------------------------------------+------------------------------------------------------+")
        self.PutModule("| geoip host         | <host>                                    | Geolocates host")
        self.PutModule("+--------------------+-------------------------------------------+------------------------------------------------------+")
        self.PutModule("| geoip nick         | <nick>                                    | Geolocates host by nick")
        self.PutModule("+--------------------+-------------------------------------------+------------------------------------------------------+")
        self.PutModule("| add                | <nick> <host> <channel>                   | Manually add a nick/host entry to the database")
        self.PutModule("+--------------------+-------------------------------------------+------------------------------------------------------+")
        self.PutModule("| merge hosts        | <url>                                     | Merges the hosts files from two users")
        self.PutModule("+--------------------+-------------------------------------------+------------------------------------------------------+")
        self.PutModule("| merge chans        | <url>                                     | Merges the chans files from two users")
        self.PutModule("+--------------------+-------------------------------------------+------------------------------------------------------+")
        self.PutModule("| config             | <variable> <value>                        | Set configuration variables per network (See README)")
        self.PutModule("+--------------------+-------------------------------------------+------------------------------------------------------+")
        self.PutModule("| getconfig          |                                           | Print the current network configuration")
        self.PutModule("+--------------------+-------------------------------------------+------------------------------------------------------+")
        self.PutModule("| save               |                                           | Manually save the latest tracks to disk")
        self.PutModule("+--------------------+-------------------------------------------+------------------------------------------------------+")
        self.PutModule("| stats              |                                           | Print nick and host stats for the network")
        self.PutModule("+--------------------+-------------------------------------------+------------------------------------------------------+")
        self.PutModule("| update             |                                           | Updates aka to latest version")
        self.PutModule("+--------------------+-------------------------------------------+------------------------------------------------------+")
        self.PutModule("| help               |                                           | Print help from the module")
        self.PutModule("+====================+===========================================+======================================================+")
