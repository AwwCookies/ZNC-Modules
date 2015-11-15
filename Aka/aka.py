# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
#   Authors: AwwCookies (Aww), MuffinMedic (Evan)                 #
#   Last Update: Nov 14, 2015                                     #
#   Version: 1.0.7                                                #
#   Desc: A ZNC Module to track users                             #
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
import collections

import requests

'''
FORCED REMOVE MOD
(Removed by MuffinMedic: lala)
requested by MuffinMedic (lala))

trace ip

Specify valid options in invalid command output

Cross ref hosts with nicks for offenses (add mask *!*) = ref ban host with nick
'''

DEFAULT_CONFIG = {
    "DEBUG_MODE": False, # 0/1
    "NOTIFY_ON_JOIN": False, # 0/1
    "NOTIFY_ON_JOIN_TIMEOUT": 300, # Seconds
    "NOTIFY_DEFAULT_MODE": "host", # host/nick
    "NOTIFY_ON_MODE": 0, # 0/1
    "NOTIFY_ON_MODERATED": 0 # 0/1
}

class aka(znc.Module):
    module_types = [znc.CModInfo.NetworkModule]
    description = "Tracks users, allowing tracing and history viewing of nicks, hosts, and channels"
    wiki_page = "aka"

    ''' OK '''
    def OnLoad(self, args, message):

        self.get_raw_kicked_host = False
        self.get_raw_geoip_host = False
        self.raw_hold = {}
        self.TIMEOUTS = {}
        self.CONFIG = {}

        self.USER = self.GetUser().GetUserName()
        self.NETWORK = self.GetNetwork().GetName()

        self.transfer_data()

        return True

    ''' OK '''
    def process_user(self, host, nick, identity, channel, message, addedWithoutMsg):
        if self.CONFIG.get("DEBUG_MODE", False):
            self.PutModule("DEBUG: Adding %s => %s" % (nick, host))

        message = str(message).replace("'","''")

        query = "SELECT * FROM users WHERE LOWER(nick) = '" + nick.lower() + "' AND LOWER(host) = '" + host.lower() + "' AND LOWER(channel) = '" + channel.lower() + "';"

        self.c.execute(query)
        data = self.c.fetchall()
        if len(data) == 0:
            if addedWithoutMsg == True:
                query = "INSERT INTO users (host, nick, channel, identity) VALUES ('" + host + "','" + nick + "','" + channel + "','" + identity + "');"
            else:
                query = "INSERT INTO users VALUES ('" + host + "','" + nick + "','" + channel + "','" + str(datetime.datetime.now()) + "','" + str(message) + "','" + identity + "');"
            self.c.execute(query)
        else:
            if addedWithoutMsg == False:
                query = "UPDATE users SET seen = '" + str(datetime.datetime.now()) + "', message = '" + str(message) + "' WHERE LOWER(nick) = '" + nick.lower() + "' AND LOWER(host) = '" + host.lower() + "' AND LOWER(channel) = '" + channel.lower() + "';"
            self.c.execute(query)
        self.conn.commit()

    ''' OK '''
    def process_moderated(self, op_nick, op_host, op_ident, channel, action, message, offender_nick, offender_host, offender_ident, added):
        if self.CONFIG.get("DEBUG_MODE", False):
            self.PutModule("DEBUG: Adding %s => %s" % (nick, host))

        message = str(message).replace("'","''")

        query = "INSERT INTO moderated VALUES('" + str(op_nick) + "','" + str(op_host) + "','" + str(channel) + "','" + str(action) + "','" + str(message) + "','" + str(offender_nick) + "','" + str(offender_host) + "','" + str(added) + "','" + str(datetime.datetime.now()) + "','" + str(offender_ident) + "','" + str(op_ident) + "');"
        self.c.execute(query)
        self.conn.commit()

    ''' OK '''
    def OnRaw(self, message):
        if self.get_raw_geoip_host:
            self.get_raw_geoip_host = False
            self.geoip_process(str(message.s).split()[5], str(message.s).split()[7])
        if self.get_raw_kicked_host:
            self.get_raw_kicked_host = False
            self.raw_hold["offender_nick"] = str(message.s).split()[7]
            self.raw_hold["offender_host"] = str(message.s).split()[5]
            self.raw_hold["offender_ident"] = str(message.s).split()[4]
            self.on_kick_process(self.raw_hold["op_nick"], self.raw_hold["op_host"], self.raw_hold["op_ident"], self.raw_hold["channel"], self.raw_hold["offender_nick"], self.raw_hold["offender_host"], self.raw_hold["offender_ident"], self.raw_hold["message"])
        if str(message.s).split()[1] == "352": # on WHO
            host = str(message.s).split()[5]
            nick = str(message.s).split()[7]
            ident = str(message.s).split()[4]
            channel = str(message.s).split()[3]
            self.process_user(host, nick, ident, channel, None, True)
        elif str(message.s).split()[1] == "311": # on WHOIS
            host = str(message.s).split()[5]
            nick = str(message.s).split()[3]
            ident = str(message.s).split()[4]
            channel = str(message.s).split()[6]
            self.process_user(host, nick, ident, channel, None, True)
        elif str(message.s).split()[1] == "314": # on WHOWAS
            host = str(message.s).split()[5]
            nick = str(message.s).split()[3]
            self.process_user(host, nick, ident, channel, None, True)

        self.raw_hold = {}

    ''' OK '''
    def OnJoin(self, user, channel):
        self.process_user(user.GetHost(), user.GetNick(), user.GetIdent(), channel.GetName(), None, True)

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
            self.process_user(user.GetHost(), new_nick, user.GetIdent(), chan.GetName(), None, True)

    ''' OK '''
    def OnPrivMsg(self, user, message):
        self.process_user(user.GetHost(), user.GetNick(), user.GetIdent(), 'PRIVMSG', message, False)

    ''' OK '''
    def OnChanMsg(self, user, channel, message):
        self.process_user(user.GetHost(), user.GetNick(), user.GetIdent(), channel.GetName(), message, False)

    ''' OK '''
    def OnChanAction(self, user, channel, message):
        message = "* " + str(message).replace("'","''")
        self.process_user(user.GetHost(), user.GetNick(), user.GetIdent(), channel.GetName(), message, False)

    ''' OK '''
    def OnPart(self, user, channel, message):
        self.process_user(user.GetHost(), user.GetNick(), user.GetIdent(), channel.GetName(), None, True)

    ''' OK '''
    def OnQuit(self, user, message, channels):
        for chan in channels:
            self.process_user(user.GetHost(), user.GetNick(), user.GetIdent(), chan.GetName(), None, True)

        if "G-Lined" in message:
            self.process_moderated(None, None, None, None, "gl", message, user.GetNick(), user.GetHost(), user.GetIdent(), None)
        elif "K-Lined" in message:
            self.process_moderated(None, None, None, None, "kl", message, user.GetNick(), user.GetHost(), user.GetIdent(), None)
        elif "Z-Lined" in message:
            self.process_moderated(None, None, None, None, "zl", message, user.GetNick(), user.GetHost(), user.GetIdent(), None)
        elif "Q-Lined" in message:
            self.process_moderated(None, None, None, None, "ql", message, user.GetNick(), user.GetHost(), user.GetIdent(), None)
        elif "Killed" in message:
            self.process_moderated(None, None, None, None, "kd", message, user.GetNick(), user.GetHost(), user.GetIdent(), None)

    ''' OK '''
    def OnKick(self, op, nick, channel, message):
        self.raw_hold["op_nick"] = op.GetNick()
        self.raw_hold["op_host"] = op.GetHost()
        self.raw_hold["op_ident"] = op.GetIdent()
        self.raw_hold["channel"] = channel.GetName()
        self.raw_hold["message"] = message

        self.get_raw_kicked_host = True
        self.PutIRC("WHO " + nick)

    ''' OK '''
    def on_kick_process(self, op_nick, op_host, op_ident, channel, offender_nick, offender_host, offender_ident, message):
        self.process_moderated(op_nick, op_host, op_ident, channel, 'k', message, offender_nick, offender_host, offender_ident, None)
        if self.CONFIG.get("NOTIFY_ON_MODERATED", True):
            self.PutModule(str(offender_nick) + " (" + str(offender_host) + ") " + " has been kicked from " + str(channel) + " by " + str(op_nick) + " (" + str(op_host) + "). Reason: " + str(message))

    ''' OK '''
    def OnMode(self, op, channel, mode, arg, added, nochange):
        mode = chr(mode)
        if added:
            char = '+'
        else:
            char = '-'

        if mode == "b" or mode == "q":
            self.process_moderated(op.GetNick(), op.GetHost(), op.GetIdent(), channel, mode, None, str(arg).split('!')[0], str(arg).split('@')[1], str((arg).split('@')[0]).split('!')[1], added)

        if (self.CONFIG["NOTIFY_ON_MODE"] == True and self.CONFIG["NOTIFY_ON_MODERATED"] == False) or (self.CONFIG["NOTIFY_ON_MODE"] == True and self.CONFIG["NOTIFY_ON_MODERATED"] == True and mode != 'b' and mode != 'q'):
            self.PutModule(str(op) + " has set mode " + str(char) + str(mode) + " " + str(arg) + " in " + str(channel))
        elif self.CONFIG.get("NOTIFY_ON_MODERATED", True) and (mode == 'b' or mode == 'q'):
            if added:
                if mode == 'b':
                    self.PutModule(str(arg).split('@')[0] + " (" + str(arg).split('@')[1] + ") has been banned from " + str(channel) + " by " + str(op) + ". Reason: " + str(arg))
                elif mode =='q':
                    self.PutModule(str(arg).split('@')[0] + " (" + str(arg).split('@')[1] + ") has been quieted in " + str(channel) + " by " + str(op) + ". Reason: " + str(arg))
            else:
                if mode == 'b':
                    self.PutModule(str(arg).split('@')[0] + " (" + str(arg).split('@')[1] + ") has been unbanned from " + str(channel) + " by " + str(op))
                elif mode =='q':
                    self.PutModule(str(arg).split('@')[0] + " (" + str(arg).split('@')[1] + ") has been unquieted in " + str(channel) + " by " + str(op))

    ''' OK '''
    def cmd_trace_nick(self, nick):
        query = "SELECT host, nick FROM users WHERE LOWER(nick) = '" + str(nick).lower() + "' GROUP BY host ORDER BY host;"
        self.c.execute(query)
        data = self.c.fetchall()
        if len(data) > 0:
            total = 0
            c2 = self.conn.cursor()
            for row in data:
                count = 0
                out = str(nick) + " was also known as: "
                query = "SELECT host, nick FROM users WHERE LOWER(host) = '" + str(row[0]).lower() + "' GROUP BY nick ORDER BY nick COLLATE NOCASE;"
                c2.execute(query)
                for row2 in c2:
                    out += row2[1] + ", "
                    count += 1
                total += count
                out = out[:-2]
                out += " (" + str(row[0]) + ")"
                self.PutModule(out + " (" + str(count) + " nicks)")
            self.PutModule(str(nick) + ": " + str(total) + " total nicks")
        else:
            self.PutModule("No history found for nick: " + str(nick))

    ''' OK '''
    def cmd_trace_host(self, host):
        query = "SELECT nick, host FROM users WHERE LOWER(host) = '" + str(host).lower() + "' GROUP BY nick ORDER BY nick COLLATE NOCASE;"
        self.c.execute(query)
        data = self.c.fetchall()
        if len(data) > 0:
            count = 0
            out = str(host) + " was known as: "
            for row in data:
                out += row[0] + ", "
                count += 1
            out = out[:-2]
            self.PutModule(out + " (" + str(count) + " nicks)")
        else:
            self.PutModule("No history found for host: " + str(host))

    ''' OK '''
    def cmd_trace_nickchans(self, nick):
        query = "SELECT DISTINCT channel FROM users WHERE LOWER(nick)  = '" + str(nick).lower() + "' AND channel IS NOT NULL ORDER BY channel;"
        self.c.execute(query)
        data = self.c.fetchall()
        if len(data) > 0:
            count = 0
            out = str(nick) + " was found in:"
            for chan in data:
                out += " " + chan[0]
                count += 1
            self.PutModule(out + " (" + str(count) + " channels)")
        else:
            self.PutModule("No channels found for nick: " + str(nick))

    ''' OK '''
    def cmd_trace_hostchans(self, host):
        query = "SELECT DISTINCT channel FROM users WHERE LOWER(host)  = '" + str(host).lower() + "' AND channel IS NOT NULL ORDER BY channel;"
        self.c.execute(query)
        data = self.c.fetchall()
        if len(data) > 0:
            count = 0
            out = str(host) + " was found in:"
            for chan in data:
                out += " " + chan[0]
                count += 1
            self.PutModule(out + " (" + str(count) + " channels)")
        else:
            self.PutModule("No channels found for host: " + str(host))

    ''' OK '''
    def cmd_trace_sharedchans(self, user_type, users):
        user_list = ''
        query = "SELECT DISTINCT channel FROM users WHERE ("
        for user in users:
            query += "LOWER(" + str(user_type) + ") = '" + str(user).lower() + "' OR "
            user_list += " " + user
        query = query[:-5]
        query += "') AND channel IS NOT NULL GROUP BY channel HAVING COUNT(DISTINCT " + user_type + ") = " + str(len(users))  + " ORDER BY channel COLLATE NOCASE;"

        self.c.execute(query)
        data = self.c.fetchall()
        if len(data) > 0:
            count = 0
            out = "Common channels between" + user_list + ": "
            for chan in data:
                out += chan[0] + " "
                count += 1
            self.PutModule(out + "(" + str(count) + " channels)")
        else:
            self.PutModule("No shared channels found for " + str(user_type) + "s:" + str(user_list))

    ''' OK '''
    def cmd_trace_intersect(self, user_type, chans):
        chan_list = ''
        query = "SELECT DISTINCT " + user_type + " FROM users WHERE "
        for chan in chans:
            query += "LOWER(channel) = '" + str(chan).lower() + "' OR "
            chan_list += " " + chan
        query = query[:-5]
        query += "' GROUP BY nick HAVING COUNT(DISTINCT channel) = " + str(len(chans))  + " ORDER BY nick COLLATE NOCASE;"

        self.c.execute(query)
        data = self.c.fetchall()
        if len(data) > 0:
            count = 0
            out = "Shared users between" + chan_list + ": "
            for nick in data:
                out += nick[0] + " "
                count += 1
            self.PutModule(out + "(" + str(count) + " " + user_type + "s)")
        else:
            self.PutModule("No common " + str(user_type) + "s found in channels:" + str(chan_list))

    ''' OK '''
    def cmd_seen(self, mode, user_type, channel, user):
        if mode == "in":
            if channel == 'PRIVMSG':
                chan = 'Private Message'
            else:
                chan = channel
            query = "SELECT seen, message FROM users WHERE seen = (SELECT MAX(seen) FROM users WHERE LOWER(nick) = '" + str(user).lower() + "' AND LOWER(channel) = '" + str(channel).lower() + "') AND LOWER(nick) = '" + str(user).lower() + "' AND LOWER(channel) = '" + str(channel).lower() + "';"
            self.c.execute(query)
            data = self.c.fetchall()
            if len(data) > 0:
                for row in data:
                    days, hours, minutes = self.dt_diff(row[0])
                    self.PutModule(str(user) + " was last seen in " + str(chan) + " " + str(days) + " days, " + str(hours) + " hours, " + str(minutes) + " minutes ago" + " saying \"" + str(row[1]) + "\" (" + str(row[0]) + ")")
            else:
                self.PutModule(str(user_type).title() + " " + str(user) + " has not been seen in " + str(chan))
        elif mode == "nick" or mode == "host":
            query = "SELECT channel, MAX(seen), message FROM users WHERE seen = (SELECT MAX(seen) FROM users WHERE LOWER(" + str(mode) + ") = '" + str(user).lower() + "') AND LOWER(" + str(mode) + ") = '" + str(user).lower() + "';"
            self.c.execute(query)
            data = self.c.fetchall()
            if data[0][0] != None:
                for row in data:
                    if row[0] == 'PRIVMSG':
                        chan = 'Private Message'
                    else:
                        chan = channel
                    days, hours, minutes = self.dt_diff(row[1])
                    self.PutModule(str(user) + " was last seen in " + str(row[0]) + " " + str(days) + " days, " + str(hours) + " hours, " + str(minutes) + " minutes ago" + " saying \"" + str(row[2]) + "\" (" + str(row[1]) + ")")
            else:
                self.PutModule(str(user_type).title() + " " + str(user) + " has not been seen.")

    ''' OK '''
    def cmd_offenses(self, method, user_type, user, channel):
        query = ''
        cols = "op_nick, op_host, channel, action, message, offender_nick, offender_host, added, time"
        if method == "user":
            if user_type == "nick":
                query = "SELECT host, nick FROM users WHERE LOWER(nick) = '" + str(user).lower() + "' GROUP BY host ORDER BY host;"
                self.c.execute(query)
                query = "SELECT " + cols + " FROM moderated WHERE LOWER(offender_nick) = '" + str(user).lower() + "' OR LOWER(offender_nick) LIKE '" + str(user).lower() + "!%' OR LOWER(offender_nick) LIKE '" + str(user).lower() + "*%"
                for row in self.c:
                    query +=  "' OR LOWER(offender_host) = '" + str(row[0]).lower()
                query += "' ORDER BY time;"
            elif user_type == "host":
                query = "SELECT " + cols + " FROM moderated WHERE LOWER(offender_host) = '" + str(user).lower() + "' ORDER BY time;"
        elif method == "channel":
            if user_type == "nick":
                query = "SELECT host, nick FROM users WHERE LOWER(nick) = '" + str(user).lower() + "' GROUP BY host ORDER BY host;"
                self.c.execute(query)
                query = "SELECT " + cols + " FROM moderated WHERE channel = '" + str(channel) + "' AND (LOWER(offender_nick) = '" + str(user).lower() + "' OR LOWER(offender_nick) LIKE '" + str(user).lower() + "!%' OR LOWER(offender_nick) LIKE '" + str(user).lower() + "*%"
                for row in self.c:
                    query +=  "' OR LOWER(offender_host) = '" + str(row[0]).lower()
                query += "') ORDER BY time;"
            elif user_type == "host":
                query = "SELECT " + cols + " FROM moderated WHERE channel = '" + str(channel) + "' and LOWER(offender_host) = '" + str(user).lower() + "' ORDER BY time;"

        self.c.execute(query)
        data = self.c.fetchall()
        if len(data) > 0:
            count = 0
            for op_nick, op_host, channel, action, message, offender_nick, offender_host, added, time in data:
                count += 1
                if user_type == "nick":
                    offender = offender_host
                elif user_type == "host":
                    offender = offender_nick
                if action == "b" or action == "q":
                    if added == '1':
                        if action == 'b':
                            action = 'banned'
                        elif action =='q':
                            action = 'quieted'
                    else:
                        if action == 'b':
                            action = 'unbanned'
                        elif action =='q':
                            action = 'unquieted'
                    self.PutModule(str(user) + " (" + str(offender) + ")" + " was " + action + " from " + str(channel) + " by " + str(op_nick) + " on " + str(time) + ".")
                elif action == "k":
                    self.PutModule(str(user) + " (" + str(offender) + ")" + " was kicked from " + str(channel) + " by " + str(op_nick) + " on " + str(time) + ". Reason: " + str(message))
                elif action == "gl" or action == "kl" or action == "zl" or action == "ql" or action == "kd":
                    if action == "gl":
                        action = "G-Lined"
                    elif action == "kl":
                        action = "K-Lined"
                    elif action == "zl":
                        action = "Z-Lined"
                    elif action == "ql":
                        action = "Q-Lined"
                    elif action == "kd":
                        action = "Killed"

                    self.PutModule(str(user) + " (" + str(offender_host) + ")" + " was " + action + " on " + str(time) + ".")

            if method == "user":
                self.PutModule(str(user) + ": " + str(count) + " total offenses")
            elif method == "channel":
                self.PutModule(str(user) + ": " + str(count) + " total offenses in " + str(channel))
        else:
            if method == "channel":
                self.PutModule("No offenses found for " + str(user_type) + ": " + str(user) + " in " + str(channel))
            else:
                self.PutModule("No offenses found for " + str(user_type) + ": " + str(user))

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
    def cmd_add(self, nick, host, ident, channel):
        self.process_user(host, nick, ident, channel, False)
        self.PutModule("%s => %s" % (nick, host, channel))

    ''' OK '''
    def cmd_info(self):
        self.PutModule("aka nick tracking module by AwwCookies (Aww) and MuffinMedic (Evan) - http://wiki.znc.in/aka")

    ''' OK '''
    def cmd_version(self):
        """
        Pull the version number from line 4 of this script
        """
        self.PutModule(open(__file__, 'r').readlines()[3].replace("#", "").strip() + " (" + open(__file__, 'r').readlines()[2].replace("#", "").strip() +")")

    ''' OK '''
    def cmd_stats(self):
        self.c.execute('SELECT COUNT(DISTINCT host), COUNT(DISTINCT nick) FROM users;')
        for row in self.c:
            self.PutModule("Nicks: " + str(row[1]))
            self.PutModule("Hosts: " + str(row[0]))

    ''' OK '''
    def OnModCommand(self, command):
        # Valid Commands
        cmds = ["trace", "seen", "offenses", "geoip", "help", "config", "getconfig", "info", "add", "import", "export", "version", "stats", "update"]
        if command.split()[0] in cmds:
            if command.split()[0] == "trace":
                cmds = ["sharedchans", "intersect", "hostchans", "nickchans", "nick", "host", "geoip"]
                if command.split()[1] in cmds:
                    if command.split()[1] == "sharedchans":
                        cmds = ["hosts", "nicks"]
                        if command.split()[2] in cmds:
                            if command.split()[2] == "hosts":
                                type = "host"
                            elif command.split()[2] == "nicks":
                                type = "nick"
                            self.cmd_trace_sharedchans(type, list(command.split()[3:]))
                        else:
                            self.PutModule(command.split()[0] + " " + command.split()[1] + " " + command.split()[2] + " is not a valid command.")
                    elif command.split()[1] == "intersect":
                        cmds = ["hosts", "nicks"]
                        if command.split()[2] in cmds:
                            if command.split()[2] == "hosts":
                                type = "host"
                            elif command.split()[2] == "nicks":
                                type = "nick"
                            self.cmd_trace_intersect(type, command.split()[3:])
                        else:
                            self.PutModule(command.split()[0] + " " + command.split()[1] + " is not a valid command.")
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
                cmds = ["in", "nick", "host"]
                if command.split()[1] in cmds:
                    if command.split()[1] == "nick" or command.split()[1] == "host":
                        self.cmd_seen(command.split()[1], command.split()[1], None, command.split()[2])
                    elif command.split()[1] == "in":
                        cmds = ["nick", "host"]
                        if command.split()[2] in cmds:
                            self.cmd_seen(command.split()[1], command.split()[2], command.split()[3], command.split()[4])
                        else:
                            self.PutModule(command.split()[0] + " " + command.split()[1] + " " + command.split()[2] + " is not a valid command.")
                    else:
                        self.PutModule(command.split()[0] + " " + command.split()[1] + " is not a valid command.")
                else:
                    self.PutModule(command.split()[0] + " " + command.split()[1] + " is not a valid command.")
            elif command.split()[0] == "offenses":
                cmds = ["in", "nick", "host"]
                if command.split()[1] in cmds:
                    if command.split()[1] == "nick":
                        self.cmd_offenses("user", "nick", command.split()[2], None)
                    elif command.split()[1] == "host":
                        self.cmd_offenses("user", "host", command.split()[2], None)
                    elif command.split()[1] == "in":
                        if command.split()[2] == "nick":
                            self.cmd_offenses("channel", "nick", command.split()[4], command.split()[3])
                        elif command.split()[2] == "host":
                            self.cmd_offenses("channel", "host", command.split()[4], command.split()[3])
                        else:
                            self.PutModule(command.split()[0] + " " + command.split()[1] + " " + command.split()[2] + " is not a valid command.")
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
                self.cmd_add(command.split()[1], command.split()[2], command.split()[3], command.split()[4])
            elif command.split()[0] == "help":
                self.cmd_help()
            elif command.split()[0] == "import":
                self.cmd_import_json(command.split()[1])
            elif command.split()[0] == "export":
                cmds = ["host", "nick"]
                if command.split()[1] in cmds:
                    self.cmd_export_json(command.split()[2], command.split()[1])
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
    def dt_diff(self, td):
        time = td.split('.', 1)[0]
        then = datetime.datetime.strptime(time, "%Y-%m-%d %H:%M:%S")
        now = datetime.datetime.now()
        diff = now - then
        days = diff.days
        hours = diff.seconds//3600
        minutes = (diff.seconds//60)%60
        return days, hours, minutes

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
            elif var_name == "NOTIFY_ON_MODERATED":
                if int(value) in [0, 1]:
                    if int(value) == 0:
                        self.CONFIG["NOTIFY_ON_MODERATED"] = False
                        self.PutModule("Notify On Moderated: OFF")
                    elif int(value) == 1:
                        self.CONFIG["NOTIFY_ON_MODERATED"] = True
                        self.PutModule("Notify On Moderated: ON")
                else:
                    self.PutModule("Valid values: 0, 1")
            else:
                self.PutModule("%s is not a valid var." % var_name)
        with open(self.GetSavePath() + "/config.json", 'w') as f:
            f.write(json.dumps(self.CONFIG, sort_keys=True, indent=4))

    ''' OK '''
    def update(self):
        if self.GetUser().IsAdmin():
            new_version = urllib.request.urlopen("https://raw.githubusercontent.com/AwwCookies/ZNC-Modules/master/Aka/aka.py")
            with open(self.GetModPath(), 'w') as f:
                f.write(new_version.read().decode('utf-8'))
                self.PutModule("aka successfully updated.")
                znc.CModule().UpdateModule('aka')
        else:
            self.PutModule("You must be an administrator to update this module.")

    ''' OK '''
    def db_setup(self):
        self.conn = sqlite3.connect(self.GetSavePath() + "/aka." + self.NETWORK + ".db")
        self.c = self.conn.cursor()
        self.c.execute("create table if not exists users (host, nick, channel, seen, identity, UNIQUE(host COLLATE NOCASE, nick COLLATE NOCASE, channel COLLATE NOCASE));")
        self.c.execute("create table if not exists moderated (op_nick, op_host, channel, action, message, offender_nick, offender_host, offender_ident, added, time)")

        ''' ADDITIONAL TABLES '''
        self.c.execute("PRAGMA table_info(users);")
        exists = False
        for table in self.c:
            if str(table[1]) == 'identity':
                exists = True
        if exists == False:
            self.c.execute("ALTER TABLE users ADD COLUMN identity;")

        self.c.execute("PRAGMA table_info(users);")
        exists = False
        for table in self.c:
            if str(table[1]) == 'message':
                exists = True
        if exists == False:
            self.c.execute("ALTER TABLE users ADD COLUMN message;")

        self.c.execute("PRAGMA table_info(moderated);")
        exists = False
        for table in self.c:
            if str(table[1]) == 'offender_ident':
                exists = True
        if exists == False:
            self.c.execute("ALTER TABLE moderated ADD COLUMN offender_ident;")

        self.c.execute("PRAGMA table_info(moderated);")
        exists = False
        for table in self.c:
            if str(table[1]) == 'op_ident':
                exists = True
        if exists == False:
            self.c.execute("ALTER TABLE moderated ADD COLUMN op_ident;")

        self.c.execute("PRAGMA table_info(moderated);")
        exists = False
        for table in self.c:
            if str(table[1]) == 'identity':
                exists = True
        if exists == True:
            self.c.execute("BEGIN TRANSACTION")
            self.c.execute("CREATE TEMPORARY TABLE mod_backup(op_nick, op_host, channel, action, message, offender_nick, offender_host, added, time, offender_ident, op_ident)")
            self.c.execute("INSERT INTO mod_backup SELECT op_nick, op_host, channel, action, message, offender_nick, offender_host, added, time, offender_ident, op_ident FROM moderated")
            self.c.execute("DROP TABLE moderated")
            self.c.execute("CREATE TABLE moderated(op_nick, op_host, channel, action, message, offender_nick, offender_host, added, time, offender_ident, op_ident)")
            self.c.execute("INSERT INTO moderated SELECT op_nick, op_host, channel, action, message, offender_nick, offender_host, added, time, offender_ident, op_ident FROM mod_backup")
            self.c.execute("DROP TABLE mod_backup")
            self.c.execute("COMMIT")
            self.conn.commit()

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
        elif not os.path.exists(self.GetSavePath() + "/config.json"):
            self.CONFIG = DEFAULT_CONFIG
            with open(self.GetSavePath() + "/config.json", 'w') as f:
                f.write(json.dumps(self.CONFIG, sort_keys=True, indent=4))

        if os.path.exists(self.GetSavePath() + "/hosts.json") and os.path.exists (self.GetSavePath() + "/hosts.json"):

            self.PutModule("aka needs to migrate your data to the new database format. Your data has been backed up. This may take a few minutes and will only happen once.")

            chans = {}
            chans = json.loads(open(self.GetSavePath() + "/chans.json", 'r').read())

            for chan in chans:
                for user in chans[chan]:
                    query = "INSERT OR IGNORE INTO users (host, nick, channel) VALUES ('" + str(user[1]) + "','" + str(user[0]) + "','" + str(chan) + "');"
                    self.c.execute(query)
                del user
            del chans[chan]
            self.conn.commit()

            hosts = {}
            hosts = json.loads(open(self.GetSavePath() + "/hosts.json", 'r').read())
            for host in hosts:
                for nick in hosts[host]:
                        query = "INSERT OR IGNORE INTO users (host, nick) VALUES ('" + str(host) + "','" + str(nick) + "');"
                        self.c.execute(query)
                del nick
            del hosts[host]
            self.conn.commit()

            self.c.execute("VACUUM")

            shutil.move(self.GetSavePath() + "/hosts.json", self.GetSavePath() + "/hosts_processed.json")
            shutil.move(self.GetSavePath() + "/chans.json", self.GetSavePath() + "/chans_processed.json")

            self.PutModule("Data migration complete.")

    ''' OK '''
    def cmd_import_json(self, url):
        count = 0
        json_object = json.loads(requests.get(url).text)
        for user in json_object:
            self.c.execute("INSERT OR IGNORE INTO users (host, nick) VALUES ('" + str(user["host"]) + "','" + str(user["nick"]) + "');")
            count += 1
        self.conn.commit()
        self.PutModule(str(count) + " users imported successfully.")

    ''' OK '''
    def cmd_export_json(self, user, type):
        if type == "host":
            subtype = "nick"
        elif type == "nick":
            subtype = "host"
        result_array = []
        query = "SELECT nick, host FROM users WHERE LOWER(" + type + ") = '" + str(user).lower() + "' GROUP BY " + subtype
        self.c.execute(query)
        if type == "nick":
            for row in self.c:
                c2 = self.conn.cursor()
                c2.execute("SELECT nick, host FROM users WHERE LOWER(" + subtype + ") = '" + str(row[1]).lower() + "' GROUP BY " + type)
                for row2 in c2:
                    d = collections.OrderedDict()
                    d["nick"] = row2[0]
                    d["host"] = row2[1]
                    result_array.append(d)
        elif type == "host":
            for row in self.c:
                d = collections.OrderedDict()
                d["nick"] = row[0]
                d["host"] = row[1]
                result_array.append(d)

        user = str(user).replace("/",".")

        with open(self.GetSavePath() + "/" + user + ".json", 'w') as f:
            f.write(json.dumps(result_array, sort_keys = True, indent = 4))

        self.PutModule("Exported file saved to: " + self.GetSavePath() + "/" + user + ".json")

    ''' OK '''
    def cmd_help(self):
        self.PutModule("+==========================+===========================================+======================================================+")
        self.PutModule("| Command                  | Arguments                                 | Description                                          |")
        self.PutModule("+==========================+===========================================+======================================================+")
        self.PutModule("| trace nick               | <nick>                                    | Shows nick change and host history for given nick    |")
        self.PutModule("+--------------------------+-------------------------------------------+------------------------------------------------------+")
        self.PutModule("| trace host               | <host>                                    | Shows nick history for given host                    |")
        self.PutModule("+--------------------------+-------------------------------------------+------------------------------------------------------+")
        self.PutModule("| trace sharedchans nicks  | <nick1> <nick2> ... <nick#>               | Show common channels between a list of nicks         |")
        self.PutModule("+--------------------------+-------------------------------------------+------------------------------------------------------+")
        self.PutModule("| trace sharedchans hosts  | <host1> <host2> ... <host#>               | Show common channels between a list of hosts         |")
        self.PutModule("+--------------------------+-------------------------------------------+------------------------------------------------------+")
        self.PutModule("| trace intersect nicks    | <#channel1> <#channel2> ... <#channel#>   | Display nicks common to a list of channels           |")
        self.PutModule("+--------------------------+-------------------------------------------+------------------------------------------------------+")
        self.PutModule("| trace intersect hosts    | <#channel1> <#channel2> ... <#channel#>   | Display hosts common to a list of channels           |")
        self.PutModule("+--------------------------+-------------------------------------------+------------------------------------------------------+")
        self.PutModule("| trace nickchans          | <nick>                                    | Get all channels a nick has been seen in             |")
        self.PutModule("+--------------------------+-------------------------------------------+------------------------------------------------------+")
        self.PutModule("| offenses nick            | <nick>                                    | Display kick/ban/quiet history for nick              |")
        self.PutModule("+--------------------------+-------------------------------------------+------------------------------------------------------+")
        self.PutModule("| offenses host            | <host>                                    | Display kick/ban/quiet history for host              |")
        self.PutModule("+--------------------------+-------------------------------------------+------------------------------------------------------+")
        self.PutModule("| offenses in nick         | <channel> <nick>                          | Display kick/ban/quiet history for nick in channel   |")
        self.PutModule("+--------------------------+-------------------------------------------+------------------------------------------------------+")
        self.PutModule("| offenses in host         | <channel> <host>                          | Display kick/ban/quiet history for host in channel   |")
        self.PutModule("+--------------------------+-------------------------------------------+------------------------------------------------------+")
        self.PutModule("| seen nick                | <nick>                                    | Displays last time nick was seen speaking globally   |")
        self.PutModule("+--------------------------+-------------------------------------------+------------------------------------------------------+")
        self.PutModule("| seen host                | <host>                                    | Displays last time host was seen speaking globally   |")
        self.PutModule("+--------------------------+-------------------------------------------+------------------------------------------------------+")
        self.PutModule("| seen in nick             | <#channel> <nick>                         | Displays last time nick was seen speaking in channel |")
        self.PutModule("+--------------------------+-------------------------------------------+------------------------------------------------------+")
        self.PutModule("| seen in host             | <#channel> <host>                         | Displays last time host was seen speaking in channel |")
        self.PutModule("+--------------------------+-------------------------------------------+------------------------------------------------------+")
        self.PutModule("| geoip host               | <host>                                    | Geolocates host                                      |")
        self.PutModule("+--------------------------+-------------------------------------------+------------------------------------------------------+")
        self.PutModule("| geoip nick               | <nick>                                    | Geolocates host by nick                              |")
        self.PutModule("+--------------------------+-------------------------------------------+------------------------------------------------------+")
        self.PutModule("| add                      | <nick> <host> <channel>                   | Manually add a nick/host entry to the database       |")
        self.PutModule("+--------------------------+-------------------------------------------+------------------------------------------------------+")
        self.PutModule("| import                   | <url>                                     | Imports user data to DB from valid JSON file url     |")
        self.PutModule("+--------------------------+-------------------------------------------+------------------------------------------------------+")
        self.PutModule("| export nick              | <nick>                                    | Exports nick data to JSON file                       |")
        self.PutModule("+--------------------------+-------------------------------------------+------------------------------------------------------+")
        self.PutModule("| export host              | <host>                                    | Exports host data to JSON file                       |")
        self.PutModule("+--------------------------+-------------------------------------------+------------------------------------------------------+")
        self.PutModule("| config                   | <variable> <value>                        | Set configuration variables per network (See README) |")
        self.PutModule("+--------------------------+-------------------------------------------+------------------------------------------------------+")
        self.PutModule("| getconfig                |                                           | Print the current network configuration              |")
        self.PutModule("+--------------------------+-------------------------------------------+------------------------------------------------------+")
        self.PutModule("| save                     |                                           | Manually save the latest tracks to disk              |")
        self.PutModule("+--------------------------+-------------------------------------------+------------------------------------------------------+")
        self.PutModule("| stats                    |                                           | Print nick and host stats for the network            |")
        self.PutModule("+--------------------------+-------------------------------------------+------------------------------------------------------+")
        self.PutModule("| update                   |                                           | Updates aka to latest version                        |")
        self.PutModule("+--------------------------+-------------------------------------------+------------------------------------------------------+")
        self.PutModule("| help                     |                                           | Print help from the module                           |")
        self.PutModule("+==========================+===========================================+======================================================+")
