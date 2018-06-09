*feediverse* will read RSS/Atom feeds and send the messages as Mastodon posts.
Please use responsibly! *feediverse* is kind of the same thing as [feed2toot]
but it's just one module that works with Python 3 ... and I was bored.

## Install

    pip install feediverse

## Run

The first time you run *feediverse* you'll need to tell it your Mastodon
instance and get an access token which it will save in a configuration file. If
you don't specify a config file it will use `~/.feediverse`:

    feediverse

Once *feediverse* is configured you can add it to your crontab:

    */15 * * * * /usr/local/bin/feediverse    

## Post Format

You can customize the post format by opening the configuration file (default is
~/.feediverse) and updating the *template* property of your feed. The default
format is:

    {title} {url}

If you want you can use `{summary}` in your template, and add boilerplate text
like so:

    Bookmark: {title} {url} {summary}

`{hashtags}` will look for tags in the feed entry and turn them into a space
separated list of hashtags.

## Multiple Feeds

Since *feeds* is a list you can add additional feeds to watch if you want.

    ...
    feeds:
      - url: https://example.com/feed/
        template: "dot com: {title} {url}"
      - url: https://example.org/feed/
        template: "dot org: {title} {url}"

## Why?

I created *feediverse* because I wanted to send my Pinboard bookmarks to
Mastodon.  I've got an IFTTT recipe that does this for Twitter, but IFTTT
doesn't appear to work with Mastodon yet. That being said *feediverse* should
work with any RSS or Atom feed (thanks to [feedparser]).

## Warning!

Please be responsible. Don't fill up Mastodon with tons of junk just because you
can. That kind of toxic behavior is why a lot of people are trying to establish
other forms of social media like Mastodon.

[feed2toot]: https://gitlab.com/chaica/feed2toot/
[feedparser]: http://feedparser.org/


