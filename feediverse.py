#!/usr/bin/env python3

import os
import re
import sys
import yaml
import codecs
import argparse
import urllib3
import dateutil
import feedparser

from bs4 import BeautifulSoup
from mastodon import Mastodon
from datetime import datetime, timezone, MINYEAR


DEFAULT_CONFIG_FILE = os.path.join("~", ".feediverse")
MAX_IMAGES = 4  # Mastodon allows attaching 4 images max.

http = urllib3.PoolManager(cert_reqs='CERT_REQUIRED',)

# encoding error-handler for buggy wordpress urls
def __urlencodereplace_errors(exc):
    bs = exc.object[exc.start:exc.end].encode("utf-8")
    bs = b"".join(b'%%%X' % b for b in bs)
    return (bs, exc.end)
codecs.register_error("urlencodereplace", __urlencodereplace_errors)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-n", "--dry-run", action="store_true",
                        help=("perform a trial run with no changes made: "
                              "don't toot, don't save config"))
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="be verbose")
    parser.add_argument("-c", "--config",
                        help="config file to use",
                        default=os.path.expanduser(DEFAULT_CONFIG_FILE))

    args = parser.parse_args()
    config_file = args.config

    if args.verbose:
        print("using config file", config_file)

    if not os.path.isfile(config_file):
        setup(config_file)        

    config = read_config(config_file)

    masto = Mastodon(
        api_base_url=config['url'],
        client_id=config['client_id'],
        client_secret=config['client_secret'],
        access_token=config['access_token']
    )

    newest_post = config['updated']
    for feed in config['feeds']:
        for entry in get_feed(feed['url'], config['updated'],
                              config['include_images'],
                              generator=feed.get('generator')):
            newest_post = max(newest_post, entry['updated'])
            if args.verbose:
                try:
                    print(entry)
                except UnicodeEncodeError:
                    # work-around for non-unicode terminals
                    print(dict(
                        (k, v.encode("utf-8") if hasattr(v, "encode") else v)
                        for k, v in entry.items()))
            if args.dry_run:
                print("trial run, not tooting ", entry["title"][:50])
                continue
            media_ids = []
            for img in entry.get("images", []):
                media = masto.media_post(img, img.headers['content-type'])
                img.release_conn()  # deferred from collect_images()
                if not 'error' in media:
                    media_ids.append(media)
            entry.pop("images", None)
            masto.status_post(feed['template'].format(**entry)[:499],
                              media_ids=media_ids)

    config['updated'] = newest_post.isoformat()
    if args.dry_run:
        print("trial run, not saving the config")
    else:
        if args.verbose:
            print("saving the config", config_file)
        save_config(config, config_file)

def save_config(config, config_file):
    copy = dict(config)
    with open(config_file, 'w') as fh:
        fh.write(yaml.dump(copy, default_flow_style=False))

def read_config(config_file):
    config = {
        'updated': datetime(MINYEAR, 1, 1, 0, 0, 0, 0, timezone.utc),
        'include_images': False,
    }
    with open(config_file) as fh:
        cfg = yaml.load(fh, yaml.SafeLoader)
        if 'updated' in cfg:
            cfg['updated'] = dateutil.parser.parse(cfg['updated'])
    config.update(cfg)
    return config

def detect_generator(feed):
    # For RSS the generator tag holds the URL, while for ATOM it holds the name
    generator = feed.feed.get("generator", "")
    if "/wordpress.org/" in generator:
        return "wordpress"
    elif "wordpress" == generator.lower():
        return "wordpress"
    return None

def get_feed(feed_url, last_update, include_images, generator=None):
    new_entries = 0
    feed = feedparser.parse(feed_url)
    if last_update:
        entries = [e for e in feed.entries
                   if dateutil.parser.parse(e['updated']) > last_update]
    else:
        entries = feed.entries
    entries.sort(key=lambda e: e.updated_parsed)
    generator = generator or detect_generator(feed)
    for entry in entries:
        new_entries += 1
        yield get_entry(entry, include_images, generator)
    return new_entries

def collect_images(entry, generator=None):

    def find_urls(part):
        if not part:
            return
        soup = BeautifulSoup(part, 'html.parser')
        for tag in soup.find_all(["a", "img"]):
            if tag.name == "a":
                url = tag.get("href")
            elif tag.name == "img":
                url = tag.get("src")
            if url and url not in urls:
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
    if generator == "wordpress":
        urls = (u for u in urls if not "/wp-content/plugins/" in u)
        # Work around a wordpress bug: If the filename contains an
        # umlaut, this will not be encoded using %-escape, as the
        # standard demands. This will break encoding in http.request()
        urls = (u.encode("ascii", "urlencodereplace").decode()
                for u in urls)
    images = []
    for url in urls:
        try:
            resp = http.request('GET', url, preload_content=False)
            if resp.headers['content-type'].startswith(("image/", "video/")):
                images.append(resp)
                # IMPORTANT: Need to release_conn() later!
                if len(images) >= MAX_IMAGES:
                    break
            else:
                resp.release_conn()
        except urllib3.exceptions.HTTPError:
            # ignore http errors, maybe they should be logged?
            pass
    return images


def get_entry(entry, include_images, generator=None):

    def cleanup(text):
        html = BeautifulSoup(text, 'html.parser')
        # Remove all elements of class read-more or read-more-*
        for more in html.find_all(None, re.compile("^read-more($|-.*)")):
            more.extract()
        text = html.get_text()
        text = re.sub('\xa0+', ' ', text)
        text = re.sub('  +', ' ', text)
        text = re.sub(' +\n', '\n', text)
        text = re.sub('\n\n\n+', '\n\n', text, flags=re.M)
        return text.strip()

    hashtags = []
    for tag in entry.get('tags', []):
        t = tag['term'].replace(' ', '_').replace('.', '').replace('-', '')
        hashtags.append('#{}'.format(t))
    summary = entry.get('summary', '')
    content = entry.get('content', '') or ''
    if content:
        content = cleanup(content[0].get('value', ''))
    url = entry.id
    if generator == "wordpress":
        links = [l for l in entry.links if l.get("rel") == "alternate"]
        if len(links) > 1:
            links = [l for l in entry.links if l.get("type") == "text/html"]
        if links:
            url = links[0]["href"]
        t = tag['term'].replace(' ', '_').replace('.', '').replace('-', '')
        hashtags.append('#{}'.format(t))
    return {
        'url': url,
        'link': entry.link,
        'title': cleanup(entry.title),
        'summary': cleanup(summary),
        'content': content,
        'hashtags': ' '.join(hashtags),
        'updated': dateutil.parser.parse(entry['updated']),
        'images': collect_images(entry, generator) if include_images else [],
        '__generator__': generator,
    }

def setup(config_file):

    def yes_no(question):
        res = input(question + ' [y/n] ')
        return res.lower() in "y1"

    url = input('What is your Mastodon Instance URL? ')
    have_app = yes_no('Do you have your app credentials already?')
    if have_app:
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
    old_posts = yes_no('Shall already existing entries be tooted, too?')
    include_images = yes_no('Shall images be included in the toot?')
    config = {
        'name': name,
        'url': url,
        'client_id': client_id,
        'client_secret': client_secret,
        'access_token': access_token,
        'include_images': include_images,
        'feeds': [
            {'url': feed_url, 'template': '{title} {url}'}
        ]
    }
    if not old_posts:
        config['updated'] = datetime.now(tz=timezone.utc).isoformat()
    save_config(config, config_file)
    print("")
    print("Your feediverse configuration has been saved to {}".format(config_file))
    print("Add a line line this to your crontab to check every 15 minutes:")
    print("*/15 * * * * /usr/local/bin/feediverse")
    print("")

if __name__ == "__main__":
    main()
