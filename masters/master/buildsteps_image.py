from worker import build_worker, workernames
import re

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


# If we trigger the build via web UI, this is the version that gets built
defaultFalterVersion = "snapshot"



def is_release_step(step):
    branch = step.getProperty("branch") or 'was_not_set'
    return re.match(".*\d+\.\d+\.\d+$", branch)


cmd_checkoutSource = Git(
    repourl='git://github.com/Freifunk-Spalter/builter',
    branch="master",   # this can get changed by html.WebStatus.change_hook()
                       # by notification from GitHub of a commit
    workdir="build/falter-builter",
    mode='full'
    )

feed_conf_interpolate = Interpolate(
    "'s/\(packages_berlin\.git\^\)\([a-f0-9]\{40,40\}\)/\1%(prop:revision)s/'"
    )

# this build wasn't triggered by feed-compilation
def no_autobuild(step):
    ver = step.getProperty("falterVersion") or None
    if ver:
        return False
    else:
        return True

set_property_falter_version = steps.SetProperty(
    property="falterVersion",
    value=defaultFalterVersion,
    doStepIf=no_autobuild
)

@renderer
def cmd_make_command(props):
    command = ['nice', './build_falter']
    command.extend(["-p", "all"])
    command.extend(["-v", props.getProperty('falterVersion', default=defaultFalterVersion)])
    # slice build parameter from builder name
    tmp_target = props.getProperty('buildername')
    target = tmp_target.split('/')[0]
    subtarget = tmp_target.split('/')[1]
    command.extend(["-t", target])
    command.extend(["-s", subtarget])
    return command


cmd_make = ShellCommand(
    name="build images",
    command=cmd_make_command,
    workdir="build/falter-builter",
    haltOnFailure=True
    )

upload_directory = Interpolate("/usr/local/src/www/htdocs/buildbot/unstable/%(prop:falterVersion:-1.1.0)s/")
upload_dir_target = Interpolate("/usr/local/src/www/htdocs/buildbot/unstable/%(prop:falterVersion:-1.1.0)s/*/%(prop:buildername)s/")

cmd_mastermkdir = MasterShellCommand(
    name="create upload-dir",
    command=[
        "mkdir",
        "-p",
        "--mode=a+rx",
        upload_directory
    ])

cmd_master_clear_dir = MasterShellCommand(
    name="clear upload-dir",
    command=[
        "/usr/local/src/clear_target.sh",
        upload_dir_target
    ])

image_worker_src_directory = Interpolate(
    "falter-builter/firmwares/"
)

cmd_uploadPackages = DirectoryUpload(
    workersrc=image_worker_src_directory,
    masterdest=upload_directory
    )

cmd_masterchmod = MasterShellCommand(
    name="make dir readable",
    command=[
        "chmod",
        "-R",
        "o+rX",
        upload_directory
    ])

cmd_masterchown = MasterShellCommand(
    name="make dir accessible",
    command=[
        "chown",
        "-R",
        "www-data:buildbot",
        upload_directory
    ]
)

cmd_cleanup = RemoveDirectory(
    dir="build/falter-builter",
    alwaysRun=True
    )

cmd_create_release_dir = MasterShellCommand(
    name="create stable-release dir",
    command=[
        "mkdir",
        "-m755",
        "-p",
        Interpolate("/usr/local/src/www/htdocs/buildbot/stable/%(prop:branch)s/")
        ],
    doStepIf=is_release_step
    )

cmd_rsync_release = MasterShellCommand(
    name="sync stable-release",
    command=[
        "rsync",
        "-av",
        "--delete",
        upload_directory,
        Interpolate("/usr/local/src/www/htdocs/buildbot/stable/%(prop:branch)s/%(prop:buildername)s")
        ],
    doStepIf=is_release_step
    )


image_factory = BuildFactory([
    cmd_checkoutSource,
    set_property_falter_version,
    cmd_mastermkdir,
    cmd_master_clear_dir,
    cmd_make,
    cmd_uploadPackages,
    cmd_masterchmod,
    cmd_masterchown,
    cmd_create_release_dir,
    cmd_rsync_release,
    cmd_cleanup
    ])

def create_builder_config(builder_name):
    return BuilderConfig(
        name=builder_name,
        workernames=workernames,
        factory=image_factory
    )

if __name__ == "__main__":
    pass