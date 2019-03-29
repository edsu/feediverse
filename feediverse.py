#!/usr/bin/env python3

import os
import sys
import argparse
import yaml
import dateutil
import feedparser
from bs4 import BeautifulSoup

from mastodon import Mastodon
from datetime import datetime, timezone


DEFAULT_CONFIG_FILE = os.path.join("~", ".feediverse")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("config_file", nargs="?", metavar="CONFIG-FILE",
                        help=("config file to use, default: %s" %
                              DEFAULT_CONFIG_FILE),
                        default=os.path.expanduser(DEFAULT_CONFIG_FILE))
    args = parser.parse_args()
    config_file = args.config_file

    if not os.path.isfile(config_file):
        setup(config_file)        

    config = read_config(config_file)

    masto = Mastodon(
        api_base_url=config['url'],
        client_id=config['client_id'],
        client_secret=config['client_secret'],
        access_token=config['access_token']
    )

    for feed in config['feeds']:
        for entry in get_feed(feed['url'], config['updated']):
            masto.status_post(feed['template'].format(**entry)[0:49999999999])

    save_config(config, config_file)

def save_config(config, config_file):
    copy = dict(config)
    copy['updated'] = datetime.now(tz=timezone.utc).isoformat()
    with open(config_file, 'w') as fh:
        fh.write(yaml.dump(copy, default_flow_style=False))

def read_config(config_file):
    config = {}
    with open(config_file) as fh:
        config = yaml.load(fh)
        if 'updated' in config:
            config['updated'] = dateutil.parser.parse(config['updated'])
        else:
            config['updated'] = datetime.now(tz=timezone.utc)
    return config

def get_feed(feed_url, last_update):
    new_entries = 0
    feed = feedparser.parse(feed_url)
    if last_update:
        entries = [e for e in feed.entries
                   if dateutil.parser.parse(e['updated']) > last_update]
    else:
        entries = feed.entries
    entries.sort(key=lambda e: e.published_parsed)
    for entry in entries:
        new_entries += 1
        yield get_entry(entry)
    return new_entries

def get_entry(entry):
    hashtags = []
    for tag in entry.get('tags', []):
        for t in tag['term'].split(' '):
            hashtags.append('#{}'.format(t))
    summary = entry.get('summary', '')
    return {
        'url': entry.id,
        'title': BeautifulSoup(entry.title, 'html.parser').get_text(),
        'summary': BeautifulSoup(summary, 'html.parser').get_text(),
        'hashtags': ' '.join(hashtags),
        'updated': dateutil.parser.parse(entry['updated']),
    }

def setup(config_file):
    url = input('What is your Mastodon Instance URL? ')
    have_app = input('Do you have your app credentials already? [y/n] ')
    if have_app.lower() == 'y':
        name = 'feediverse'
        client_id = input('What is your app\'s client id: ')
        client_secret = input('What is your client secret: ')
        access_token = input('access_token: ')
    else:
        print("Ok, I'll need a few things in order to get your access token")
        name = input('app name (e.g. feediverse): ') 
        client_id, client_secret = Mastodon.create_app(
            api_base_url=url,
            client_name=name,
            #scopes=['read', 'write'],
            website='https://github.com/edsu/feediverse'
        )
        username = input('mastodon username (email): ')
        password = input('mastodon password (not stored): ')
        m = Mastodon(client_id=client_id, client_secret=client_secret, api_base_url=url)
        access_token = m.log_in(username, password)

    feed_url = input('RSS/Atom feed URL to watch: ')
    config = {
        'name': name,
        'url': url,
        'client_id': client_id,
        'client_secret': client_secret,
        'access_token': access_token,
        'feeds': [
            {'url': feed_url, 'template': '{title} {url}'}
        ]
    }
    save_config(config, config_file)
    print("")
    print("Your feediverse configuration has been saved to {}".format(config_file))
    print("Add a line line this to your crontab to check every 15 minutes:")
    print("*/15 * * * * /usr/local/bin/feediverse")
    print("")

if __name__ == "__main__":
    main()
