import znc
import os
import urllib.request

class aka(znc.Module):
    module_types = [znc.CModInfo.NetworkModule]
    description = "Tracks users, allowing tracing and history viewing of nicks, hosts, and channels"

    def OnLoad(self, args, message):

        new_version = urllib.request.urlopen("https://raw.githubusercontent.com/emagaliff/znc-nicktrace/master/aka.py")
        with open(self.GetModPath(), 'w') as f:
            f.write(new_version.read().decode('utf-8'))

        networks = self.GetUser().GetNetworks()
        for network in networks:
            args = ''
            result = ''
            modules = network.GetModules()
            modules.ReloadModule("aka", args, self.GetUser(), network, result)

        return True
