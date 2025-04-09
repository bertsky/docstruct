# pylint: disable=unused-import

from multiprocessing import Process
from time import sleep
from random import seed, sample
import os
import pytest

from ocrd import Resolver, Workspace, OcrdMetsServer
from ocrd_utils import (
    pushd_popd,
    disableLogging,
    initLogging,
    setOverrideLogLevel,
    config,
    MIMETYPE_PAGE
)

from .assets import assets

WORKSPACES = {
    "manifesto": assets.path_to('communist_manifesto/data/mets.xml'),
    "aufklaerung": assets.path_to('kant_aufklaerung_1784/data/mets.xml'),
    "sbb": assets.path_to('SBB0000F29300010000/data/mets.xml'),
    "herrnhuterey04": assets.path_to('benner_herrnhuterey04_1748.ocrd/mets.xml'),
}

#@pytest.fixture(params=WORKSPACES.keys())
@pytest.fixture
def workspace(tmpdir, pytestconfig, asset):
    initLogging()
    if pytestconfig.getoption('verbose') > 0:
        setOverrideLogLevel('DEBUG')
    with pushd_popd(tmpdir):
        directory = str(tmpdir)
        resolver = Resolver()
        url = WORKSPACES[asset]
        workspace = resolver.workspace_from_url(url, dst_dir=directory) # download=True
        workspace.name = asset # for debugging
        # determine GT file group and download PAGE files
        gtGrp = None
        for file in workspace.find_files(mimetype=MIMETYPE_PAGE):
            if file.url.startswith("file:/"):
                # ignore broken and irrelevant groups
                workspace.remove_file(file.ID, force=True)
            elif 'GT' in file.fileGrp and (gtGrp or file.fileGrp) == file.fileGrp:
                gtGrp = file.fileGrp
                workspace.download_file(file)
        yield workspace, gtGrp
    disableLogging()

def pytest_addoption(parser):
    parser.addoption("--workspace",
                     action="append",
                     choices=list(WORKSPACES) + ["all"],
                     help="workspace(s) to run on (set 'all' to use all)"
    )

@pytest.hookimpl
def pytest_generate_tests(metafunc):
    if "asset" in metafunc.fixturenames:
        ws = metafunc.config.getoption("workspace")
        if ws == ['all']:
            ws = list(WORKSPACES)
        elif not ws:
            ws = ["aufklaerung"] # default
        metafunc.parametrize("asset", ws)

CONFIGS = ['', 'pageparallel', 'metscache', 'pageparallel+metscache']

@pytest.fixture(params=CONFIGS)
def processor_kwargs(request, workspace):
    config.OCRD_DOWNLOAD_INPUT = False # only pre-downloaded pages
    workspace, gt_grp = workspace
    config.OCRD_MISSING_OUTPUT = "ABORT" # --debug
    if 'metscache' in request.param:
        config.OCRD_METS_CACHING = True
        #print("enabled METS caching")
    if 'pageparallel' in request.param:
        config.OCRD_MAX_PARALLEL_PAGES = 4
        #print("enabled page-parallel processing")
        def _start_mets_server(*args, **kwargs):
            #print("running with METS server")
            server = OcrdMetsServer(*args, **kwargs)
            server.startup()
        process = Process(target=_start_mets_server,
                          kwargs={'workspace': workspace, 'url': 'mets.sock'})
        process.start()
        sleep(1)
        # instantiate client-side workspace
        asset = workspace.name
        workspace = Workspace(workspace.resolver, workspace.directory,
                              mets_server_url='mets.sock',
                              mets_basename=os.path.basename(workspace.mets_target))
        workspace.name = asset
        yield {'workspace': workspace, 'input_file_grp': gt_grp, 'mets_server_url': 'mets.sock'}
        process.terminate()
    else:
        yield {'workspace': workspace, 'input_file_grp': gt_grp}
    config.reset_defaults()
