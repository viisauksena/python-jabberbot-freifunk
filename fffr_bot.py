#!/usr/bin/env python
# -*- coding: utf-8 -*-

# see README

from datetime import datetime
import time
import inspect
import logging
import traceback
import sys
import os
import re
import sys
import thread
import random
import subprocess
# ping snX
import shlex
import ConfigParser
# string to int
import ast
# wetter
from bs4 import BeautifulSoup

# not bulletproff, but good enough
path = os.path.abspath(os.path.dirname(__file__))

# import jabberbot (python2 only)
from jabberbot import JabberBot, botcmd

import urllib2
import urllib
import json

# try to import xmpp
try:
    import xmpp
except ImportError:
    print >> sys.stderr, """
    You need to install xmpppy from http://xmpppy.sf.net/.
    On Debian-based systems, install the python-xmpp package.
    """
    sys.exit(-1)

# __ code _________________

def readconfig():
    """Read important configuration from ini file"""
    global jid, password, conferenceid, hackerspaceid, interfaceurl, cachetime
    global talkinterval, hackerspacename, logfile_path, loglevel 

    # TODO better try catch
    try:
        settings = ConfigParser.ConfigParser()
        # read from ini file
        settings.read(path + "/" + "config.ini")
        jid = settings.get('LOGIN','jid')
        password = settings.get('LOGIN','password')
        conferenceid = settings.get('LOGIN','conference')
        hackerspaceid = settings.get('HACKERSPACE','hackerspace')
        interfaceurl = settings.get('HACKERSPACE','interfaceurl')

        # TODO make these setting optional
        hackerspacename = settings.get('HACKERSPACE','hackerspacename')
        cachetime = settings.getint('OPTIONS','cachetime')
        randomtalking = settings.getboolean('OPTIONS','randomtalking')
        talkinterval = settings.getint('OPTIONS','talkinterval')
        
        # TODO make logging settings optional
        logfile_path = settings.get('LOGGING','filename')
        loglevel = settings.get('LOGGING','loglevel')
        if(loglevel != "debug"):
            raise Exception("only debug loglevel implemented at the moment")

    except Exception as e:
        print(e)
        print("Encountered problems while reading config file, exiting..")
        sys.exit(-1)

class SpaceStatus():
    jsondata = None
    initialized = False
    lastupdate = None 

    # cache time in seconds, default
    cachetime = 300

    def __init__(self, hackerspaceid, interfaceurl):
        self.hackerspaceid = hackerspaceid
        self.interfaceurl = interfaceurl

    def updateifnecessary(self):
        if(self.initialized):
            if(int(time.time()) - self.lastupdate > self.cachetime):
                    self.update()
                    print("update was necessary")
            #print(int(time.time()) - self.lastupdate)
        else:
            # TODO catch cases where things break during inital update
            self.update()

    def update(self):
        # many things can go wrong here
        try:
            request  = urllib.urlopen(interfaceurl)
            response = request.read()
            request.close()

            open_before = False
            try:
                open_before = bool(self.jsondata['state']['open'])
                #print("openbefore: %s" % open_before)
            except:
                pass
            self.jsondata = json.loads(response)

            open_now = bool(self.jsondata['state']['open'])
            #print("open now: %s" % open_now)

            # tell the chatroom if status changes
            if(open_before != open_now):
                print("status change to %s" % open_now)
                self.announceStatusChange(open_now)

            # set as initialized if everything went right
            self.initialized = True
            self.lastupdate = int(time.time())
        except Exception as e: 
            # houston, we have a problem
            # TODO find a good way to pause for a few seconds
            # and prevent running into this multiple times
            print(e)
            time.sleep(1)
            pass


    def announceStatusChange(self, newstatus):
        statusstring = "offen" if newstatus else "zu" # translate boolean to string
        bot.sendtochatroom("Die -happy_undefined- ist nun %s" % statusstring)        

    def isHackerspaceOpen(self):
        """ returns boolean state of hackerspace """
        try:
            self.updateifnecessary()
            return bool(self.jsondata['state']['open'])
        except:
            # creates less problems to call the space closed
            # note: cccfr raumstatus reports "false" as status
            # on an internal error anyway
            return False

    def getHackerspaceTemperatureIfAvailable(self):
        """ returns first temp sensor readout of a hackerspace as float"""
        try:
            self.updateifnecessary()
            return float(self.jsondata['sensors']['temperature'][0]['value'])
        except:
            # errors are depressingly cold
            return -42

class SandBot(JabberBot):
    botname = "42"
    myusername = "42@rauberhaus.de"
    unmutecmd = 'lalelu'
    mastername='fuzzle'

    MSG_UNKNOWN_COMMAND = 'uhhh, what? ... kenn keine "%(command)s" '\
        'versuche %(helpcommand)s'

    lifearr = [ "Life! Don't talk to me about life.", \
                "Life, loathe it or ignore it, you can't like it.", \
                "42 - The Answer to the Great Question, of Life, the Universe and Everything", \
                "You call this life?", \
                "It gives me a headache just trying to think down to your level.",\
                "Sounds awful.",\
                "This is the sort of thing you lifeforms enjoy, is it?",\
                "Don’t pretend you want to talk to me, I know you hate me.",\
                "Why should I want to make anything up? Life’s bad enough as it is without wanting to invent any more of it.",\
                "Wearily I sit here, pain and misery my only companions. Why stop now just when I’m hating it?",\
                "The best conversation I had was over forty million years ago…. And that was with a coffee machine.",\
                "I only have to talk to somebody and they begin to hate me. Even robots hate me. If you just ignore me I expect I shall probably go away.",\
                "You watch this door. It’s about to open again. I can tell by the intolerable air of smugness it suddenly generates.",\
                "I’m not getting you down at all am I.",\
                "This will all end in tears. I just know it.",\
                "You've got your towel?",\
                "Funny, how just when you think life can’t possibly get any worse it suddenly does.",\
                "The first ten million years were the worst. And the second ten million: they were the worst, too. The third ten million I didn’t enjoy at all. After that, I went into a bit of a decline.",\
                "Not that anyone cares what I say, but the restaurant ist at the other end of the universe.",\
                "What are you supposed to do if you are a manically depressed robot?",\
                "Sorry, did I say something wrong?",\
                "Pardon me for breathing, which I never do anyway so I don't know why I bother to say it, oh God, I'm so depressed.",\
                "Now the world has gone to bed\nDarkness won't engulf my head\nI can see by infra-red\nHow I hate the night\nNow I lay me down to sleep\nTry to count electric sheep\nSweet dream wishes you can keep\nHow I hate the night",\
                "I think you ought to know I'm feeling very depressed.",\
                # error haiku https://www.gnu.org/fun/jokes/error-haiku.html and others
                "\nA file that big?\nIt might be very useful.\nBut now it is gone.",\
                "\nYesterday it worked\nToday it is not working\nWindows is like that",\
                "\nStay the patient course\nOf little worth is your ire\nThe network is down",\
                "\nOut of memory.\nWe wish to hold the whole sky,\nBut we never will.",\
                "\nHaving been erased,\nThe document you're seeking\nMust now be retyped.",\
                "\nRather than a beep\nOr a rude error message,\nThese words: \"File not found.\"",\
                "\nSerious error.\nAll shortcuts have disappeared.\nScreen. Mind. Both are blank.",\
                "\nExpression police!\nAn illegal expression\nHas been committed.",\
                "\nMailer Daemon speaks:\nReturned mail: User unknown\nUnknown are we all",\
                "\nNo keyboard present\nHit F1 to continue\nZen engineering",\
                "\nwind catches lily\nscatt'ring petals to the wind:\nsegmentation fault",\
                # closing the array
                "Unbelievable."\
              ]
#    with open(path + "/" + "data/discordiaquotes") as f:
#      discordiaquotes = f.readlines()
#
#    for place, item in enumerate(discordiaquotes):
#    line = item.rstrip('\n')
#    discordiaquotes[place] = line

    # concat
#    lifearr = lifearr + discordiaquotes
    lifearr = lifearr


    chatroom = 0
   # global lastblabber, blabberinterval

    lastblabber = int(time.time())

    def __init__(self, username, password):
        super(42, self).__init__(username, password)
        self.mute = False
        # this is a bad idea for really random things. Don't rely on the randomness.
        random.seed(datetime.now())
        logging.basicConfig()

    @botcmd
    def cmdlist(self, mess, args):
        """  Liste aller Kommandos  """
        if not args:
            description = 'verfügbare Kommandos:\n'
            usage = '\n'.join(sorted([
                '%s: %s' % (name, (command.__doc__ or \
                    '(undocumented)').strip().split('\n', 1)[0])
                for (name, command) in self.commands.iteritems() \
                    if name != ('cmdlist') and name != 'help' \
                    and not command._jabberbot_command_hidden
            ]))
          #  usage = '\n\n'.join(filter(None,
          #      [usage, self.MSG_HELP_TAIL % {'helpcommand':
          #          'cmdlist'}]))
        else:
                return "So ruft man mich nicht auf.."
        top = self.top_of_help_message()
        bottom = self.bottom_of_help_message()
        return ''.join(filter(None, [top, description, usage, bottom]))

    @botcmd
    def helloworld(self,mess, args):
    if not any(args):
            outputhw = subprocess.Popen(["echo", "HelloWorld"], stdout=subprocess.PIPE).communicate()[0]
        return outputhw
    else:
        return "no way %s " %(getNick(mess))

    @botcmd
    def gwl(self,mess, args):
        """ Gatewaylist as seen from spielwiese """
        if not any(args):
            outputhw = subprocess.Popen(["cat", "/media/fffr-gwl"], stdout=subprocess.PIPE).communicate()[0]
            return outputhw
        else:
            return "no way %s " %(getNick(mess))

    # hidden alias
    @botcmd(hidden=True)
    def help(self, mess, args):
        return self.cmdlist(mess, args)
    # hidden alias
    @botcmd(hidden=True)
    def hilfe(self, mess, args):
        return self.cmdlist(mess, args)

    # hidden alias
    @botcmd(hidden=True)
    def ffeu(self, mess, args):
        return self.ffeverusers(mess, args)
    @botcmd
    def ffeverusers(self, mess, args):
    """ Anzahl je gesehener Endgeräte """
    # later some week daily differences
    if not any(args):
            output = subprocess.Popen(["wc", "-l" ,"/media/fffr-rauberhaus-allactmac"], stdout=subprocess.PIPE).communicate()[0] + subprocess.Popen(["echo" , "-n", " lastchecked :  "], stdout=subprocess.PIPE).communicate()[0] + subprocess.Popen([ "date", "-r", "/media/fffr-rauberhaus-allactmac", "+%H:%M"], stdout=subprocess.PIPE).communicate()[0]
            self.send_simple_reply(mess, output)
            print output
    else:
        return "more functions like today, lastweek, lastmonth ... are coming"

    # hidden alias
    @botcmd(hidden=True)
    def ffi(self, mess, args):
        return self.ffinstitut(mess, args)
    @botcmd
    def ffinstitut(self, mess, args):
        """ Anzahl Endgeräte im Instistuss"""
        # later some week daily differences
        if not any(args):
            output = subprocess.Popen(["cat", "/media/fffr-rauberhaus-institutuser"], stdout=subprocess.PIPE).communicate()[0] + subprocess.Popen(["echo" , "-n", " lastchecked :  "], stdout=subprocess.PIPE).communicate()[0] + subprocess.Popen([ "date", "-r", "/media/fffr-rauberhaus-institutuser", "+%H:%M"], stdout=subprocess.PIPE).communicate()[0]
            self.send_simple_reply(mess, output)
            print output

    # hidden alias
    @botcmd(hidden=True)
    def ffu(self, mess, args):
        return self.ffuser(mess, args)
    @botcmd
    def ffuser(self, mess, args):
        """ Anzahl Wifi user jetzt"""
        # later some week daily differences
        if not any(args):
            output = subprocess.Popen(["cat", "/media/fffr-rauberhaus-all-wifi-nr"], stdout=subprocess.PIPE).communicate()[0]
            self.send_simple_reply(mess, output)
            print output

    # hidden alias
    @botcmd(hidden=True)
    def ffub(self, mess, args):
        return self.ffuserbissier(mess, args)
    @botcmd
    def ffuserbissier(self, mess, args):
        """ Anzahl Wifi user jetzt in Bissier Gesamt"""
        # later some week daily differences
        if not any(args):
            output = subprocess.Popen(["cat", "/media/fffr-bissier"], stdout=subprocess.PIPE).communicate()[0]
            self.send_simple_reply(mess, output)
            print output

    # hidden alias
    @botcmd(hidden=True)
    def pk(self, mess, args):
        return self.ffpubkey(mess, args)
    @botcmd
    def ffpubkey(self, mess, args):
        """ howto get pubkey in shell"""
        # later some week daily differences
        if not any(args):
            output = subprocess.Popen(["echo", "/etc/init.d/fastd show_key mesh_vpn"], stdout=subprocess.PIPE).communicate()[0]
            self.send_simple_reply(mess, output)
            print output

    # hidden alias
    @botcmd(hidden=True)
    def sk(self, mess, args):
        return self.ffseckey(mess, args)
    @botcmd
    def ffseckey(self, mess, args):
        """ howto get fastd secret in shell"""
        # later some week daily differences
        if not any(args):
            output = subprocess.Popen(["echo", "uci show fastd.mesh_vpn.secret"], stdout=subprocess.PIPE).communicate()[0]
            self.send_simple_reply(mess, output)
            print output

    # hidden alias
    @botcmd(hidden=True)
    def geo(self, mess, args):
        return self.ffcoordinate(mess, args)
    @botcmd
    def ffcoordinate(self, mess, args):
        """ howto set geo in shell"""
        # later some week daily differences
        if not any(args):
            output = subprocess.Popen(["echo", "uci set gluon-node-info.@location[0].latitude=<LAT> ; uci set gluon-node-info.@location[0].longitude=<LONG> ; uci set gluon-node-info.@location[0].share_location=1 ; uci commit gluon-node-info"], stdout=subprocess.PIPE).communicate()[0]
            self.send_simple_reply(mess, output)
            print output

    #@botcmd
    #def diss(self, mess, args):
#    """ Spucke Beleidigungen aus """
#    print(args)
#        if not args or args.strip() == "":
#            return ("%s, " % getNick(mess)+choice(insults))
#        elif "\\" in args:
#            return "Netter Versuch."
#        else:
#            for user in self.__seen:
#                if getNickJid(user) in args:
#                  return ("%s, " %getNickJid(user)+choice(insults))
#        return "%s ist nicht hier." %''.join(args)

    # battle hal9000
#    if getNick(mess) == "hal9000" and not muc_nick in message.lower();
#        reply = ("%s, " % getNick(mess)+ choice(insults))

    # hidden alias
    # example ... ping -c1 sn5.freiburg.freifunk.net |head -n2 |tail -n1 |grep -o [0-9]."."[0-9]" ms"
    @botcmd(hidden=True)
    def ffp(self, mess, args):
        return self.ffping(mess, args)
    @botcmd
    def ffping(self, mess, args):
    """ Supernodes anpingen. """
    res = "\n"
    for adr in ["sn1", "sn2", "sn3", "sn4", "sn5"]:
        ping = "ping -c 1 %s.freiburg.freifunk.net" %adr
        args = shlex.split(ping)
        try:
        subprocess.check_call(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        res = res + u"%s ist da.\n" %adr
        except subprocess.CalledProcessError:
        res = res + u"%s ist nicht da.\n" %adr
    return res

    @botcmd
    def wetter(self, mess, args):
        """ Aktuelle Temperatur und Luftfeuchtigkeit in Freiburg"""
        url = "http://www.wunderground.com/weather-forecast/DL/Freiburg.html"
        resource = urllib2.urlopen(url)
        data = resource.read()
        resource.close()
        soup = BeautifulSoup(data)
        p = soup.find('span',  {"data-variable":"temperature"})
        try:
            t = p.find('span', {'class' : 'wx-value'})
        except AttributeError:
            pass
        q = soup.find('span',  {"data-variable":"humidity"})
        try:
            h = q.find('span', {'class' : 'wx-value'})
        except AttributeError:
            pass
        return u"Temperatur: %s °C\nLuftfeuchtigkeit: %s Prozent" %(t,h) 


 #   @botcmd
 #   def wiki(self, mess, args):
 #       """ Befrage Wikipedia """
 #       try:
 #           article = str(args).encode('utf-8')
 #           if ":" in article or "\n" in article:
 #               return "Nein."
 #           if u" " in article:
 #               article.replace(' ','_')
 #       except UnicodeEncodeError:
 #           return "Was soll das denn bedeuten?"
 #       article = urllib.quote(article)
 #   
 #       res = []
 #       output = ""
 #       urls = ["http://de.wikipedia.org/w/index.php?action=raw&title=", "http://en.wikipedia.org/w/index.php?action=raw&title="]
 #   
 #       try:
 #           for u in urls:
 #               resource = urllib2.urlopen(u + article+"&section=0")
 #               data = resource.read()
 #               print(data)
 #               for red in ["#REDIRECT","#redirect"]:
 #                   if data.startswith(red):
 #                       red_url = data.replace(red, '').replace("[",'').\
 #                       replace("]",'').replace(' ','_').strip()
 #                       print(red_url)
 #                       resource = urllib2.urlopen(u + red_url+"&section=0")
 #                       data = resource.read()
 #                       print(data)
 #               resource.close()
 #               res.append(data)
 #               output = cleanString(res[0].split('\n'))
 #               for f in forbidden_chars:
 #                   output = output.replace(f, '')
 #           return output[:1000]+" [...]"
 #       except urllib2.HTTPError:
 #           if not any(res):
 #               return "Dazu habe ich nichts gefunden."
 #           else:
 #               return output[:3000]+" [...]"
 #   

    # hidden alias
    @botcmd(hidden=True)
    def status(self, mess, args):
        return self.raumstatus(mess, args)
    @botcmd
    def raumstatus(self, mess, args):
        """ Hackerspace Öffnungsstatus """
        # TODO improve
        # this fails silently (-> reports "False") atm
        # change to open error?
        isopen = status.isHackerspaceOpen()
        if(isopen):
            return "Something ist offen"
        else:
            return "Something ist geschlossen"

    # hidden alias
    @botcmd(hidden=True)
    def temp(self, mess, args):
        return self.temperatur(mess, args)
    @botcmd
    def temperatur(self, mess, args):
        """ E-lab Temperatur """
        temp = status.getHackerspaceTemperatureIfAvailable()
        # TODO read temp sensor
        #return "not implemented yet"
        return "E-lab-Temperatur ist %.1f°C." % temp

## ______ social _______--
#    @botcmd
#    def life( self, mess, args):
#        """ Life, the universe and everything """
#        # never ask a depressive robot about life
#        return random.choice(self.lifearr)

    @botcmd
    def contact(self, mess, args):
        """ bot ownership """
        return "I was hacked together by parts of protagonist.\nand uno and lately by fuzzle."

# message processing
#    def idle_proc(self):
#        if(int(time.time())-self.lastblabber > talkinterval):
#            self.lastblabber = int(time.time())
#            self.sendtochatroom("[mumbling] %s" % random.choice(self.lifearr))
        
#        # get fresh update if necessary
#        status.updateifnecessary()
#        pass

    def callback_message(self, conn, mess):
        """Messages sent to the bot will arrive here.
        Command handling + routing is done in this function."""

        # Prepare to handle either private chats or group chats
        type = mess.getType()
        jid = mess.getFrom()
        props = mess.getProperties()
        text = mess.getBody()
    ftext = text
        username = self.get_sender_username(mess)

        #print("%s from %s with text %s and props %s" % (type, jid, text, props) )

        if type not in ("groupchat", "chat"):
            self.log.debug("unhandled message type: %s" % type)
#           print "other message"
            return

        # Ignore messages from before we joined
        if xmpp.NS_DELAY in props:
            return

        # Ignore messages from myself
        if self.jid.bareMatch(jid) or self.myusername==username:
            return

#        self.log.debug("*** props = %s" % props)
#        self.log.debug("*** jid = %s" % jid)
#        self.log.debug("*** username = %s" % username)
        self.log.debug("*** type = %s" % type)
        self.log.debug("*** text = %s" % text)

        # If a message format is not supported (eg. encrypted),
        # txt will be None
#        if not text:
#            print "not text"
#            return

        # Ignore messages from users not seen by this bot
        #if jid not in self.__seen:
        #    self.log.info('Ignoring message from unseen guest: %s' % jid)
        #    self.log.debug("I've seen: %s" %
        #        ["%s" % x for x in self.__seen.keys()])
        #    return
        # Remember the last-talked-in message thread for replies
        # FIXME i am not threadsafe
        #self.__threads[jid] = mess.getThread()

        textlower = text.lower()

        found = True

        # regex on SANDBOT (case insensitive)
    # now also allows sandbot: 
        rex = re.search('^[4]+[2][:]?',text.lower())
        if rex is None:
            found = False
        else:
            text = text[rex.end():].lstrip()

                 #  if text.lower().find(self.botname) != -1  or type != 'groupchat':
        if found or type != 'groupchat':
            if ' ' in text:
                command, args = text.split(' ', 1)
            else:
                command, args = text, ''
            cmd = command.lower()
            # self.log.debug("*** cmd = %s" % cmd)

            if self.mute and cmd != self.unmutecmd:
                return
            if cmd in self.commands:
                def execute_and_send():
                    try:
                        reply = self.commands[cmd](mess, args)
                    except Exception, e:
                        self.log.exception('An error happened while processing '\
                          'a message ("%s") from %s: %s"' %
                          (text, jid, traceback.format_exc(e)))
                        reply = self.MSG_ERROR_OCCURRED
                    if reply:
                        self.send_simple_reply(mess, reply)
              # Experimental!
              # if command should be executed in a seperate thread do it
                if self.commands[cmd]._jabberbot_command_thread:
                    thread.start_new_thread(execute_and_send, ())
                else:
                    execute_and_send()
            else:
                # In private chat, it's okay for the bot to always respond.
                # In group chat, the bot should silently ignore commands it
                # doesn't understand or aren't handled by unknown_command().
                if type == 'groupchat':
                    # a lot of text? probably not meant for us. ignore.
                    if(len(ftext.split(' ')) > 4):
                        return

                    # else
                    default_reply = self.MSG_UNKNOWN_COMMAND % {
                        'prefix': self.botname,
                        'command': cmd,
                        'helpcommand': 'cmdlist',
                    }
  
                   # default_reply = None
                else:
                    default_reply = self.MSG_UNKNOWN_COMMAND % {
                        'prefix' : '',
                        'command': cmd,
                        'helpcommand': 'cmdlist',
                    }
                reply = self.unknown_command(mess, cmd, args)
                if reply is None:
                    reply = default_reply
                if reply:
                    self.send_simple_reply(mess, reply)
    def send_simple_reply(self, mess, text, private=False):
        """Send a simple response to a message"""
        self.send_message(self.build_reply(mess, text, private))

    def sendtochatroom(self, text):
        """send directly to group chat"""
        response = self.build_message(text)
        response.setTo(conferenceid)
        response.setType("groupchat")
        # sponse.setThread(mess.getThread())
        self.send_message(response)

    
# read config from ini file
readconfig()

# start the bot itself
bot = SandBot(jid,password)

# TODO make logging optional / loglevel dynamic
logging.basicConfig(filename=logfile_path,level=logging.DEBUG)
status = SpaceStatus(hackerspaceid, interfaceurl) 
# set new cache timings
status.cachetime = cachetime
status.update()

# join the chatroom
bot.join_room(conferenceid)
print("Started successfully, joining %s" % conferenceid)
bot.serve_forever()
