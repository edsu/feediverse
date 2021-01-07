*feediverse* will read RSS/Atom feeds and send the messages as Mastodon posts.
Please use responsibly! *feediverse* is kind of the same thing as [feed2toot]
but it's just one module that works with Python 3, and I was bored.

## Install

    pip install feediverse

## Run

The first time you run *feediverse* you'll need to tell it your Mastodon
instance and get an access token which it will save in a configuration file. If
you don't specify a config file it will use `~/.feediverse`:

    feediverse

Once *feediverse* is configured you can add it to your crontab:

    */15 * * * * /usr/local/bin/feediverse    

Run `feediverse --help` to show the command line options.


## Post Format

You can customize the post format by opening the configuration file (default is
~/.feediverse) and updating the *template* property of your feed. The default
format is:

    {title} {url}

If you want you can use `{summary}` in your template, and add boilerplate text
like so:

    Bookmark: {title} {url} {summary}

`{hashtags}` will look for tags in the feed entry and turn them into a space
separated list of hashtags. For some feeds (e.g. youtube-rss) you should use `{link}` instead of `{url}`.

`{content}` is the whole content of the feed entry (with html-tags
stripped). Please be aware that this might easily exceed Mastodon's
limit of 512 characters.


## Multiple Feeds

Since *feeds* is a list you can add additional feeds to watch if you want.

    ...
    feeds:
      - url: https://example.com/feed/
        template: "dot com: {title} {url}"
      - url: https://example.org/feed/
        template: "dot org: {title} {url}"
        generator: wordpress


## Special Handling for Different Feed Generators

*feediverse* has support for some special cases of some feed
generators. For example detecting the entries perma-link. Currently
only Wordpress is handled, but others may follow.

If a feed does not provide a proper *generator* entry, you can set it
by adding a `generator:` value to the feed's configuration. See the
seconds one in the example above.

You can check whether feed provides a *generator* entry like this:

    feediverse --verbose --dry-run feedverse-test.rc | grep generator

## Why?

I created *feediverse* because I wanted to send my Pinboard bookmarks to
Mastodon.  I've got an IFTTT recipe that does this for Twitter, but IFTTT
doesn't appear to work with Mastodon yet. That being said *feediverse* should
work with any RSS or Atom feed (thanks to [feedparser]).

## Warning!

Please use responsibly. Don't fill up Mastodon with tons of junk just because
you can. That kind of toxic behavior is why a lot of people are trying to
establish other forms of social media like Mastodon.

[feed2toot]: https://gitlab.com/chaica/feed2toot/
[feedparser]: http://feedparser.org/

