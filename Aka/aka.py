import znc
import os
import urllib.request

DEFAULT_CONFIG = {
    "DEBUG_MODE": False, # 0/1
    "NOTIFY_ON_JOIN": False, # 0/1
    "NOTIFY_ON_JOIN_TIMEOUT": 300, # Seconds
    "NOTIFY_DEFAULT_MODE": "host", # host/nick
    "NOTIFY_ON_MODE": False, # 0/1
    "NOTIFY_ON_MODERATED": False # 0/1
}

class aka(znc.Module):
    module_types = [znc.CModInfo.NetworkModule]
    description = "Tracks users, allowing tracing and history viewing of nicks, hosts, and channels"
    wiki_page = "aka"

    ''' PROCESS DATA '''
    def OnLoad(self, args, message):

        self.update()

        return True

    def update(self):
        new_version = urllib.request.urlopen("https://raw.githubusercontent.com/emagaliff/znc-nicktrace/master/aka.py")
        with open(self.GetModPath(), 'w') as f:
            f.write(new_version.read().decode('utf-8'))
            self.PutModule("aka successfully updated. Please reload aka on all networks.")
        
        networks = self.GetUser().GetNetworks()
        for network in networks:
            args = ''
            result = ''
            modules = network.GetModules()
            modules.ReloadModule("aka", args, self.GetUser(), network, result)
