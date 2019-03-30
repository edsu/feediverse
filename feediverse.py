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
import urllib3


DEFAULT_CONFIG_FILE = os.path.join("~", ".feediverse")

http = urllib3.PoolManager(cert_reqs='CERT_REQUIRED',)

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
            media_ids = []
            for img in entry.get("images", []):
                media = masto.media_post(img, img.headers['content-type'])
                img.release_conn()  # deferred from collect_images()
                if not 'error' in media:
                    media_ids.append(media)
            entry.pop("images", None)
            masto.status_post(feed['template'].format(**entry)[:49999999999],
                              media_ids=media_ids)
    save_config(config, config_file)

def save_config(config, config_file):
    copy = dict(config)
    copy['updated'] = datetime.now(tz=timezone.utc).isoformat()
    with open(config_file, 'w') as fh:
        fh.write(yaml.dump(copy, default_flow_style=False))

def read_config(config_file):
    config = {}
    with open(config_file) as fh:
        config = yaml.load(fh, yaml.SafeLoader)
        if 'updated' in config:
            config['updated'] = dateutil.parser.parse(config['updated'])
        else:
            config['updated'] = datetime.now(tz=timezone.utc)
    return config

def detect_generator(feed):
    # For RSS the generator tag holds the URL, while for ATOM it holds the name
    if "/wordpress.org/" in feed.feed.generator:
        return "wordpress"
    elif "wordpress" == feed.feed.generator.lower():
        return "wordpress"
    return None

def get_feed(feed_url, last_update):
    new_entries = 0
    feed = feedparser.parse(feed_url)
    if last_update:
        entries = [e for e in feed.entries
                   if dateutil.parser.parse(e['updated']) > last_update]
    else:
        entries = feed.entries
    entries.sort(key=lambda e: e.published_parsed)
    generator = detect_generator(feed)
    for entry in entries:
        new_entries += 1
        yield get_entry(entry, generator)
    return new_entries

def collect_images(entry):

    def find_urls(part):
        if not part:
            return
        soup = BeautifulSoup(part, 'html.parser')
        for tag in soup.find_all(["a", "img"]):
            if tag.name == "a":
                url = tag["href"]
            elif tag.name == "img":
                url = tag["src"]
            if url not in urls:
                urls.append(url)

    urls = []
    find_urls(entry.get("summary", ""))
    for c in entry.get("content", []):
        find_urls(c.value)
    for e in (entry.enclosures
              + [l for l in entry.links if l.get("rel") == "enclosure"]):
        if (e["type"].startswith(("image/", "video/")) and
            e["href"] not in urls):
            urls.append(e["href"])
    images = []
    for url in urls:
        resp = http.request('GET', url, preload_content=False)
        if resp.headers['content-type'].startswith(("image/", "video/")):
            images.append(resp)
            # IMPORTANT: Need to release_conn() later!
        else:
            resp.release_conn()
    return images


def get_entry(entry, generator=None):
    hashtags = []
    for tag in entry.get('tags', []):
        for t in tag['term'].split():
            hashtags.append('#' + t)
    summary = entry.get('summary', '')
    content = entry.get('content', '')
    url = entry.id
    if generator == "wordpress":
        links = [l for l in entry.links if l.get("rel") == "alternate"]
        if len(links) > 1:
            links = [l for l in entry.links if l.get("type") == "text/html"]
        if links:
            url = links[0]["href"]
    return {
        'url': url,
        'title': BeautifulSoup(entry.title, 'html.parser').get_text(),
        'summary': BeautifulSoup(summary, 'html.parser').get_text(),
        'content': BeautifulSoup(summary, 'html.parser').get_text(),
        'hashtags': ' '.join(hashtags),
        'updated': dateutil.parser.parse(entry['updated']),
        'images': collect_images(entry),
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
