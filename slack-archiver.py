#!/usr/bin/env python

import sys
sys.dont_write_bytecode = True

import time
import logging
import time
import yaml
import json
import os
import sys
import codecs
import re

from slackclient import SlackClient



class SlackArchiver(object):
    def __init__(self, config):
        self.last_ping = 0
        self.token = config['SLACK_TOKEN']
        self.slack_client = None
        self.channels = dict()
        self.users = dict()
        self.history = dict()
        self.sliding_window = 100


        self.archive_root = config['ARCHIVE_DIR']
        dir = os.path.dirname(self.archive_root)

        try:
            os.stat(dir)
        except:
            os.mkdir(dir)

        self.load_channel_timestamps()

    def connect(self):
        """Convenience method that creates Server instance"""
        print "Connecting with " + self.token
        self.slack_client = SlackClient(self.token)


    def start(self):
        """Connecting to the Slack API fetching all channels for archiving"""
        self.connect()
        all_channels = self.get_channels()
        all_users = self.get_users()


        for a_channel in self.channels:
            print "Archiving channel: " + a_channel
            self.archive_channel(a_channel)

        # after all channels have been archived
        # write out the timestamps to the history file
        self.write_channel_timestamps()

    def get_users(self):

        """Get the list of users and store them in dictionary for easier use"""
        # https://api.slack.com/methods/users.list
        response = self.slack_client.api_call("users.list", token=self.token)

        members = json.loads(response)
        if debug:
            logging.info("User list")
            logging.info(json.dumps(members, indent=4, sort_keys=True))

        users = members['members']

        for user in users:
            self.users[user['id']] = user


    def get_channels(self):
        """Get the list of channels and store name & id in dictionary for easier use"""
        # https://api.slack.com/methods/channels.info
        params = {"token": self.token}


        channel_list = self.slack_client.api_call("channels.list",token=self.token )



        data = json.loads(channel_list)


        if debug:
            logging.info("Channel List")
            logging.info(json.dumps(data, indent=4, sort_keys=True))


        channels = data['channels']
        for chanel in channels:
            channel_id = chanel['id']
            self.channels[channel_id] = chanel

    def archive_channel(self, channel_id):
        """fetches history of a given channel and writes the entries out to a file"""

        channel_id_latest = 1.0
        response = ""
        has_more = True
        iterator = 0

        logentry = list()

        channel = self.channels[channel_id]
        channel_name = channel['name']

        print ("Channel ID:" + channel_id)
        print ("Channel Name:" + channel_name)


        # if channel is found in history then
        # use timestamp from there
        # otherwise start with history = 0
        ts_latest = float(time.time())
        if channel_id in self.history:
            ts_oldest = self.history[channel_id]
        else:
            self.history[channel_id] = 0
            ts_oldest = 0

        # open the archive file for appending
        archiveFile =  codecs.open(self.archive_root + channel_name + ".archive.txt","a+", "utf-8")

        while has_more:
            # if the channel_id is found in the history dictionary
            # use this timestamp as oldest
            iterator = iterator + 1

            print "This is iteration number: " + str(iterator) + " for channel: " + channel_name

            # request channel history
            response = self.slack_client.api_call("channels.history", token=self.token, channel=channel_id, oldest=ts_oldest, latest=ts_latest, count=self.sliding_window, inclusive=0)

            # parse response JSON
            history = json.loads(response)


            # reset the has more status
            if history['has_more']:
                has_more = True
            else:
                has_more = False

            # the actual messages
            messages = history['messages']

            if debug:
                print "Found " + str(len(messages)) + " new messages in " + channel_name

            for entry in messages:

                # find the oldest entry in current response
                if float(entry['ts']) < ts_latest:
                    ts_latest = float(entry['ts'])

                # update the state keeping entry
                if self.history[channel_id] < entry['ts']:
                    self.history[channel_id] = entry['ts']

                # append entry to list so we can write out in reverse order
                logentry.append(self.parse_history_entry(entry, channel_id))

        # finally update the history keeping with the newest entry
        while len(logentry) > 0:
            archiveFile.write(logentry.pop() + "\n")

        archiveFile.close()


    def parse_history_entry(self, history_entry, channel_id):
        """parse a single history line and decode username, timestamp etc. """

        logentry = ""

        # we want to retain only the messages
        if history_entry['type'] == "message":
            #do message
            timestamp = self.format_ts(history_entry['ts'])

            if "subtype" in history_entry:
                subtype = history_entry['subtype']
                print "subtype: " + subtype


            # extract the user who posted the message
            if "user" in history_entry:
                user_id = history_entry['user']
                username = self.get_name_for_id(user_id)
            else:
                username = "none"

            # get the verbose channel name
            channel = self.channels[channel_id]
            channel_name = channel['name']
            try:
                self.extract_urls(history_entry['text'])
            except KeyError as e:
                print "Problem with history_entry"
                print history_entry

            try:
                parsed_text = self.resolve_usernames(history_entry['text'])
            except KeyError as e:
                print "Problem with history_entry"
                print history_entry
                username = "unkown"
                parsed_text = "unknown"

            logentry = timestamp +": <" + username + "> " + parsed_text
        else:
            
            print "History type: " + history_entry['type'] + " => " + history_entry['text']

        return logentry


    def extract_urls(self, message):
        """this method formats the output for subtype file_share"""
        p = re.compile('<http[s]?://.*>')
        urls = p.findall(message)

        linkfile =  codecs.open("linksammlung.archive.txt","a+", "utf-8")
        for url in urls:
            if debug:
                try:
                    print "URL: " + url
                except UnicodeEncodeError as e:
                    print "Can't print URL as it contains special characters. URL but written to file."
            linkfile.write(url + "\n")
        linkfile.close()


    def get_name_for_id(self, userid):

        username = "none"
        try:
            # look up the user in our user object
            user = self.users[userid]
            username = user['name']
        except KeyError:
            # if we don't find the user then just use the user_id
            username = userid
        return username


    def resolve_usernames(self, textmessage):
        t = textmessage
        p = re.compile('<@(\w*)>')
        usernames = p.findall(t)
        # print "Length of matches: " + str(len(usernames))
        for userid in usernames:
            t = t.replace(userid , self.get_name_for_id(userid))

        return t



    def load_channel_timestamps(self):

        hist = None
        try:
            with open('channel.history', 'r') as fp:
                hist = json.load(fp)
                fp.close()
                self.history = hist
        except ValueError:
            logging.info("can't find valid JSON structure in channel history file")

        except IOError:
            print "history file not found. Will create new one"



    def write_channel_timestamps(self):
        """write the dictionary of timestamps of the channels to a file so we can start where we've left off next time"""
        with open('channel.history', 'w') as outfile:
                json.dump(self.history, outfile )
                outfile.close()


    def format_ts(self, ts):
        """convert the epoch time stamps into a human readable format"""
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(float(ts)))
        return timestamp




# main class
def main_loop():

    # if logfile is defined in config, then use it
    if "LOGFILE" in config:
        logging.basicConfig(filename=config["LOGFILE"], level=logging.INFO, format='%(asctime)s %(message)s')
    logging.info(directory)


    # start the archiver
    try:
        archiver.start()
    except KeyboardInterrupt:
        sys.exit(0)
    except:
        logging.exception('OOPS')

if __name__ == "__main__":
    directory = os.path.dirname(sys.argv[0])
    if not directory.startswith('/'):
        directory = os.path.abspath("{}/{}".format(os.getcwd(),
                                directory
                                ))

    config = yaml.load(file('slack.conf', 'r'))
    debug = config["DEBUG"]
    archiver = SlackArchiver(config)

    if config.has_key("DAEMON"):
        if config["DAEMON"]:
            import daemon
            with daemon.DaemonContext():
                main_loop()
    main_loop()
