from setuptools import setup

with open("README.md") as f:
    long_description = f.read()

setup(
    name='feediverse',
    version='0.0.1',
    url='https://github.com/edsu/feediverse',
    author='Ed Summers',
    author_email='ehs@pobox.com',
    py_modules=['feediverse', ],
    description='Connect an RSS Feed to Mastodon',
    long_description=long_description,
    long_description_content_type="text/markdown",
    install_requires=['feedparser', 'mastodon.py', 'python-dateutil', 'pyyaml'],
    entry_points={'console_scripts': ['feediverse = feediverse:main']}
)
