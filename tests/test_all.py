# pylint: disable=import-error

import os
import pytest

from ocrd import Workspace, run_processor
from ocrd_models.constants import NAMESPACES as NS

from docstruct.proc import OcrdDocStruct

# from ocrd_pagetopdf
def get_structure(mets):
    metsroot = mets._tree.getroot()
    structlink = metsroot.find('mets:structLink', NS)
    smlinks = {link.get('{http://www.w3.org/1999/xlink}from'):
               link.get('{http://www.w3.org/1999/xlink}to')
               for link in reversed(structlink.findall('./mets:smLink', NS)
                                    if structlink is not None else [])}
    phymap = metsroot.find('mets:structMap[@TYPE="PHYSICAL"]', NS)
    topdiv = next(phymap.iterfind('./mets:div', NS))
    pages = {page.get('ID'): page.get('ORDER') or order
             for order, page in enumerate(topdiv.findall('./mets:div', NS))
             if page.get('TYPE') == "page"}
    logmap = metsroot.find('mets:structMap[@TYPE="LOGICAL"]', NS)
    if logmap is None:
        return None
    if (topdiv := logmap.find('./mets:div', NS)) is None:
        return None
    # descend to deepest ADM
    while (topdiv.get('ADMID') is None and
           (div := topdiv.find('./mets:div', NS)) is not None):
        topdiv = div
    # we want to dive into multivolume_work, periodical, newspaper, year, month...
    # we are looking for issue, volume, monograph, lecture, dossier, act, judgement, study, paper, *_thesis, report, register, file, fragment, manuscript...
    while ((div := topdiv.find('./mets:div', NS)) is not None and
           div.get('ADMID') is not None):
        topdiv = div
    #for div in topdiv.iterdescendants('{%s}div' % NS['mets']):
    # recursive:
    def find_depth(div, depth=0):
        div_id = div.get('ID', div.getparent().get('ID'))
        return {
            'label': div.get('LABEL') or div.get('ORDERLABEL') or '',
            'type': div.get('TYPE') or '',
            'id': div_id,
            'page': pages.get(smlinks.get(div_id, ''), ''),
            'depth': depth,
            'subs': [find_depth(subdiv, depth+1)
                     for subdiv in div.findall('./mets:div', NS)]
        }
    struct = find_depth(topdiv)
    return struct

def test_docstruct(processor_kwargs):
    ws = processor_kwargs['workspace']
    input_file_grp = processor_kwargs['input_file_grp']
    if not input_file_grp:
        pytest.skip(f"workspace asset '{ws.name}' has no PAGE GT fileGrp")
    offline_ws = Workspace(ws.resolver, ws.directory, mets_basename=os.path.basename(ws.mets_target))
    structure_old = get_structure(offline_ws.mets)
    run_processor(OcrdDocStruct,
                  output_file_grp="", # as long as core#1321 is open, we must something here
                  parameter=dict(mode="enmap"),
                  **processor_kwargs,
    )
    ws.save_mets()
    offline_ws.reload_mets()
    structure_new = get_structure(offline_ws.mets)
    assert structure_old != structure_new
