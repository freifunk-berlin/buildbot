from buildbot.process.factory import BuildFactory
from buildbot.config import BuilderConfig
from buildbot.plugins import steps
from buildbot.steps.source.git import Git
from buildbot.steps.shell import ShellCommand
from buildbot.steps.transfer import DirectoryUpload
from buildbot.steps.master import MasterShellCommand
from buildbot.process.properties import Interpolate, renderer, Property
from buildbot.steps.worker import RemoveDirectory
from datetime import date
import re


def is_release(step):
    branch = step.getProperty("falterVersion") or 'was_not_set'
    return re.match(".*\d+\.\d+\.\d+$", branch)

def is_no_release(step):
    branch = step.getProperty("falterVersion") or 'was_not_set'
    return not re.match(".*\d+\.\d+\.\d+$", branch)


feed_checkoutSource = Git(
    repourl='git://github.com/freifunk-berlin/falter-repo_builder',
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
    Interpolate('src-git falter https://github.com/freifunk-berlin/falter-packages^%(prop:revision)s'),
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
freifunk_release_path = Interpolate("https://raw.githubusercontent.com/freifunk-berlin/falter-packages/%(prop:revision)s/packages/falter-common/files-common/etc/freifunk_release")

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

feed_trigger_image_generation_snapshot = steps.Trigger(
    name="trigger generation of new snapshot images",
    schedulerNames=["trigger_snapshots"],
    waitForFinish = False,
    alwaysUseLatest = True,
    set_properties={"falterVersion" : Property("falterVersion")},
    doStepIf=is_no_release
)

feed_trigger_image_generation_release = steps.Trigger(
    name="trigger generation of release images",
    schedulerNames=["trigger_release"],
    waitForFinish = False,
    alwaysUseLatest = True,
    set_properties={"falterVersion" : Property("falterVersion")},
    doStepIf=is_release
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
    feed_cleanup_tmp,
    feed_trigger_image_generation_snapshot,
    feed_trigger_image_generation_release
    ])

def create_feed_builder(builder_name):
    return BuilderConfig(
        name=builder_name,
        workernames=['ionos-worker01', 'ionos-worker02'],
        factory=feed_factory
    )

if __name__ == "__main__":
    pass
