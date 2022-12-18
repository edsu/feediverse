*feediverse* will read RSS/Atom feeds and send the messages as Mastodon posts.
It's meant to add a little bit of spice to your timeline from other places.
Please use it responsibly.

## Build Locally

Check out this repository, and then run the following commands:

    pip install wheel
    pip install .

[Source](https://towardsdatascience.com/building-a-python-package-without-publishing-e2d36c4686cd)

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

