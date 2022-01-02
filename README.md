# Buildbot for Freifunk Firmware

NOTE: The buildbot configuration is now handled in the ansible-repo exclusively. Please go there for issues and changes. This repository is archived.

The [Freifunk Firmware (Berlin)](https://github.com/freifunk-berlin/firmware) is automatically built by the [buildbot](http://buildbot.berlin.freifunk.net).

This repo contains the buildbot config for the master and slaves.

## Contribute a buildbot slave
You can add your server easily as a buildbot slave in order to help us build the firmwares. Please write a mail to the [mailing list](http://lists.berlin.freifunk.net/cgi-bin/mailman/listinfo/berlin) and ask for a password (please include a name for the host).

### Installation via docker
The easiest way to configure your buildbot slave is to use docker. Once you've installed docker on your system you can run the [buildbot slave docker image](https://github.com/freifunk-berlin/buildbot-slave-docker).

### Manual installation on Debian/Ubuntu
On a Debian/Ubuntu machine, the following steps have to be carried out:

1. Install all dependencies that are listed for [freifunk-berlin/firmware](https://github.com/freifunk-berlin/firmware).
2. Install the buildslave:

  ```
  sudo apt-get install python-dev python-virtualenv
  virtualenv --no-site-packages sandbox
  source sandbox/bin/activate
  easy_install sqlalchemy==0.7.10 buildbot buildbot-slave
  buildslave create-slave --umask=022 slave firmware.berlin.freifunk.net:9989 HOSTNAME PASSWORD
  ```

On Ubuntu you can also use the package provided by the package manager:

http://zverovich.net/2012/06/16/installing-buildbot-in-ubuntu.html

3. Fill `slave/info/admin` with your name and mail (in case we need to contact you about a changed configuration)
4. ```buildslave start slave```

##### After a reboot or new login
```
virtualenv --no-site-packages sandbox
source sandbox/bin/activate
```
The buildbot can then be started or stopped with
```buildslave start slave``` or ```buildslave stop slave```.
