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
from slackclient import SlackClient



class SlackArchiver(object):
    def __init__(self, config):
        self.last_ping = 0
        self.token = config['SLACK_TOKEN']
        self.slack_client = None
        self.channels = dict()
        self.users = dict()

        self.archive_root = config['ARCHIVE_DIR']
        dir = os.path.dirname(self.archive_root)

        try:
            os.stat(dir)
        except:
            os.mkdir(dir)

    def connect(self):
        """Convenience method that creates Server instance"""
        print "Connecting with " + self.token
        self.slack_client = SlackClient(self.token)
    def start(self):
        self.connect()
        all_channels = self.get_channels()
        all_users = self.get_users()


        for a_channel in self.channels:
            print "Archiving channel: " + a_channel
            self.archive_channel(a_channel)

    def get_users(self):
        # https://api.slack.com/methods/users.list
        response = self.slack_client.api_call("users.list", token=self.token)
        if debug:
            logging.info("User List")
            logging.info(response)


        members = json.loads(response)
        users = members['members']

        for user in users:
            self.users[user['id']] = user


    def get_channels(self):
        # https://api.slack.com/methods/channels.info
        params = {"token": self.token}
        print self.slack_client.api_call("channels.info", channel="1234567890")

        channel_list = self.slack_client.api_call("channels.list",token=self.token )
        if debug:
            logging.info("Channel List")
            logging.info(channel_list)


        data = json.loads(channel_list)

        channels = data['channels']
        for chanel in channels:
            channel_id = chanel['id']
            self.channels[channel_id] = chanel

    def archive_channel(self, channel_id):
        response = self.slack_client.api_call("channels.history", token=self.token, channel=channel_id, )
        history = json.loads(response)

        channel = self.channels[channel_id]
        channel_name = channel['name']


        archiveFile = file = codecs.open(channel_name + ".text","w", "utf-8")

        if debug:
            logging.info("History: ")
            logging.info(response)

        messages = history['messages']

        for entry in messages:
            logentry = self.parse_history_entry(entry, channel_id)
            archiveFile.write(logentry + "\n")

        archiveFile.close()

    def parse_history_entry(self, history_entry, channel_id):
        logentry = ""

        if history_entry['type'] == "message":
            #do message
            timestamp = self.format_ts(history_entry['ts'])

            if "user" in history_entry:
                user_id = history_entry['user']
                user = self.users[user_id]
                username = user['name']
            else:
                username = "none"

            channel = self.channels[channel_id]
            channel_name = channel['name']


            logentry = timestamp +": <" + username + ">[" + channel_name + "] " + history_entry['text']
        else:
            print "History type: " + history_entry['type'] + " => " + history_entry['text']

        return logentry






    def format_ts(self, ts):
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
    files_currently_downloading = []

    if config.has_key("DAEMON"):
        if config["DAEMON"]:
            import daemon
            with daemon.DaemonContext():
                main_loop()
    main_loop()
