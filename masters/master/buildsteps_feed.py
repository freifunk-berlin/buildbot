from buildbot.process.factory import BuildFactory
from buildbot.config import BuilderConfig
from buildbot.plugins import steps
from buildbot.steps.source.git import Git
from buildbot.steps.shell import ShellCommand
from buildbot.steps.transfer import DirectoryUpload
from buildbot.steps.master import MasterShellCommand
from buildbot.process.properties import Interpolate, renderer
from buildbot.steps.worker import RemoveDirectory
from datetime import date
from requests import get
import re


feed_checkoutSource = Git(
    repourl='git://github.com/Freifunk-Spalter/repo_builder',
    branch="master",   # this can get changed by html.WebStatus.change_hook()
                       # by notification from GitHub of a commit
    workdir="build",
    alwaysUseLatest=True,
    mode='full'
    )


feed_create_tmpdir = ShellCommand(
    name="create tmp dir",
    command=[
    "mkdir",
    "-p",
    "tmp"]
    )


@renderer
def feed_make_command(props):
    command = ['nice',
	'./build_all_targets',
	'19.07.5',
        Interpolate('src-git falter https://github.com/Freifunk-Spalter/packages.git;%(prop:buildername)s'),
        Interpolate('%(prop:builddir)s/tmp'),
        'build_parallel'
        ]
    return command

feed_make = ShellCommand(
    name="build feed",
    command=feed_make_command,
    haltOnFailure=True
    )

# fetch upload-dir from FREIFUNK_RELEASE variable in freifunk_release file.
# this file shows the falter-version the feed is intended for
freifunk_release_path = Interpolate("https://raw.githubusercontent.com/Freifunk-Spalter/packages/%(prop:revision)s/packages/falter-common/files-common/etc/freifunk_release")

def extract_falter_dir(rc, stdout, stderr):
    try:
        versionString = re.search("FREIFUNK_RELEASE=['\"](.*)['\"]", stdout)
        falterVersion = versionString.group(1)
    except:
        falterVersion = 'unknown'

    return {'falterVersion': falterVersion}


feed_get_falter_release_as_property = steps.SetPropertyFromCommand (
    name="fetch falter-version",
    command=["wget", freifunk_release_path, "-O", "-"],
    extract_fn=extract_falter_dir
    )


upload_dir = Interpolate("/usr/local/src/www/htdocs/buildbot/feed/%(prop:falterVersion)s/")

feed_master_empty_dir = MasterShellCommand(
    name="clear upload dir",
    command=[
        "rm",
        "-rf",
        upload_dir
        ]
)

feed_mastermkdir = MasterShellCommand(
    name="create upload dir",
    command=[
        "mkdir",
        "-p",
        "--mode=a+rx",
        upload_dir
        ]
)

worker_src_dir = Interpolate("%(prop:builddir)s/tmp/")
feed_uploadPackages = DirectoryUpload(
    workersrc=worker_src_dir,
    masterdest=upload_dir
    )

feed_masterchmod = MasterShellCommand(
    name="chmod upload dir",
    command=[
        "chmod",
        "-R",
        "o+rX",
        upload_dir
    ])

feed_sign_packages = MasterShellCommand(
    name="sign packages",
    command=[
        "/usr/local/src/sign_packages.sh",
        upload_dir
        ]
)

feed_cleanup = RemoveDirectory(
    dir="build",
    alwaysRun=True
    )

feed_cleanup_tmp = RemoveDirectory(
    dir=Interpolate('%(prop:builddir)s/tmp'),
    alwaysRun=True
)

feed_factory = BuildFactory([
    feed_checkoutSource,
    feed_create_tmpdir,
    feed_get_falter_release_as_property,
    feed_master_empty_dir,
    feed_make,
    feed_mastermkdir,
    feed_uploadPackages,
    feed_masterchmod,
    feed_sign_packages,
    feed_cleanup,
    feed_cleanup_tmp
    ])

def create_feed_builder(builder_name):
    return BuilderConfig(
        name=builder_name,
        workernames=['ionos-worker01', 'ionos-worker02'],
        factory=feed_factory
    )

if __name__ == "__main__":
    pass