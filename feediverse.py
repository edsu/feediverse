#!/usr/bin/env python3

import os
import sys
import yaml
import dateutil
import feedparser

from mastodon import Mastodon
from datetime import datetime, timezone

def main():
    config_file = get_config_file()
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
            masto.status_post(feed['template'].format(**entry))

    save_config(config, config_file)

def get_config_file():
    if __name__ == "__main__" and len(sys.argv) > 1:
        config_file = sys.argv[1]
    else:
        config_file = os.path.join(os.path.expanduser("~"), ".feediverse")
    return config_file

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
    for entry in feed.entries:
        e = get_entry(entry)
        if last_update is None or e['updated'] > last_update:
            new_entries += 1
            yield e
    return new_entries

def get_entry(entry):
    hashtags = []
    for tag in entry.get('tags', []):
        for t in tag['term'].split(' '):
            hashtags.append('#{}'.format(t))
    return {
        'url': entry.id,
        'title': entry.title,
        'summary': entry.get('summary', ''),
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
