slack-archiver
=============
This is an archiver for your Slack account. The idea is to archive the content
of all channels in regular intervals for you to keep a local copy.

It's based on the Python code of the [SlackClient](https://github.com/slackhq/python-slackclient) provided by Slack from

The script will write a logfile per channel and keeps a statefile of when it
fetched the last messages from the channels. So it can pickup on subsequent runs
where it has left off last time. This reduces the number of API calls.

A separate file is written which contains all URLs from all channel messages as
an aggregated link archive.


Dependencies
----------
* websocket-client https://pypi.python.org/pypi/websocket-client/
* python-slackclient https://github.com/slackhq/python-slackclient

Installation
-----------

1. Download the slack-archiver code

        git clone git@github.com:maxheadroom/slack-archiver.git
        cd slack-archiver

2. Install dependencies ([virtualenv](http://docs.python-guide.org/en/latest/dev/virtualenvs/) is recommended.)

        pip install -r requirements.txt

3. Configure slack-archiver (https://api.slack.com/bot-users)

        cp slack.conf.example slack.conf
        vi slack.conf
          SLACK_TOKEN: "xoxb-11111111111-222222222222222"

4. Run the archiver

        python slack-archiver.py


*Note*: At this point slack-archiver is ready to run.


####Todo:
Latest version can writes channel timestamps into a file to pick up where it has left of before.
