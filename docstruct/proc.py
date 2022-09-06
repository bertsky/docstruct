import click
from lxml import etree as ET

from ocrd import Processor
from ocrd.decorators import ocrd_cli_options, ocrd_cli_wrap_processor
from ocrd_utils import (
    getLogger,
    assert_file_grp_cardinality,
    xywh_from_points,
    xywh_from_bbox,
    bbox_from_xywh
)
from ocrd_modelfactory import page_from_file
from ocrd_models.ocrd_page import to_xml
from ocrd_models.ocrd_mets import OcrdMets

from ocrd_models.ocrd_mets import OcrdMets
from ocrd_models.constants import (
    NAMESPACES as NS,
    TAG_METS_DIV,
    TAG_METS_FPTR,
    TAG_METS_STRUCTMAP,
)

from .config import OCRD_TOOL

# should go into ocrd_models.constants:
TAG_METS_STRUCTLINK = '{%s}structLink' % NS['mets']
TAG_METS_SMLINK = '{%s}smLink' % NS['mets']
TAG_METS_AREA = '{%s}area' % NS['mets']
TAG_METS_SEQ = '{%s}seq' % NS['mets']

TOOL = 'ocrd-docstruct'

class OcrdDocStruct(Processor):

    def __init__(self, *args, **kwargs):
        kwargs['ocrd_tool'] = OCRD_TOOL['tools'][TOOL]
        kwargs['version'] = OCRD_TOOL['version']
        super().__init__(*args, **kwargs)
        self.last_result = [] 
        self.log_links = {}
        self.first = None

    def create_logmap_smlink(self):
        LOG = getLogger('OcrdDocStruct')
        el_root = self.workspace.mets._tree.getroot()
        self.log = el_root.find('mets:structMap[@TYPE="LOGICAL"]', NS)
        if self.log is None:
            self.log = ET.SubElement(el_root, TAG_METS_STRUCTMAP)
            self.log.set('TYPE', 'LOGICAL')
            LOG.info('mets:structMap LOGICAL created')
        else:
            LOG.warning('mets:structMap LOGICAL already exists, adding to it')
        self.log_map = {div.get('ID'): div for div in self.log.xpath('.//mets:div', namespaces=NS)}
        self.log_ids = [id_ for id_ in self.log_map.keys() if id_ and id_.startswith("LOG_")]
        self.phy_ids = self.workspace.mets.physical_pages
        self.link = el_root.find(TAG_METS_STRUCTLINK)
        if self.link is None and self.parameter['mode'] != 'enmap':
            self.link = ET.SubElement(el_root, TAG_METS_STRUCTLINK)
        self.link_map = dict()
        if self.link is not None:
            for smlink in self.link.findall(TAG_METS_SMLINK):
                smlink_phy = smlink.get('{' + NS['xlink'] + '}to')
                smlink_log = smlink.get('{' + NS['xlink'] + '}from')
                self.link_map.setdefault(smlink_phy, list()).append(smlink_log)

    def process(self):
        """
        """
        LOG = getLogger('OcrdDocStruct')
        assert_file_grp_cardinality(self.input_file_grp, 1)
        mode = self.parameter['mode'] # enmap/mets:area or dfg/mets:structLink
        # FIXME: more parameters (what kind of region types, geometric rules etc)

        self.create_logmap_smlink()

        results = []
        for input_file in self.input_files:
            page_id = input_file.pageId or input_file.ID
            LOG.info("INPUT FILE %s", page_id)
            pcgts = page_from_file(self.workspace.download_file(input_file))
            page = pcgts.get_Page()
            if page.get_type() in ['front-cover', 'back-cover', 'title', 'blank']:
                LOG.info("skipping page type %s", page.get_type())
                continue
            if page.get_type() in ['table-of-contents', 'index']:
                # FIXME use directly
                LOG.info("skipping page type %s", page.get_type())
            results.extend(self.extract_text(page, input_file))
        self.write_to_mets(results)

    def extract_text(self, page, input_file):
        """
        get text regions in reading order, put them into a hierarchy (via heuristic rules)
        """
        LOG = getLogger('OcrdDocStruct')
        target = self.parameter['type']
        result = []
        # FIXME: what about non-text regions (tables, images)?
        for region in page.get_AllRegions(classes=['Text']):
            subtype = region.get_type()
            # FIXME: geometric rules approximating this
            if subtype in ['caption',
                           'header',
                           'footer',
                           'page-number',
                           'drop-capital',
                           'credit',
                           'signature-mark',
                           'catch-word',
                           'marginalia',
                           'footnote',
                           'footnote-continued',
                           'endnote']:
                # skip non-linear elements
                continue
            # FIXME: use TOC-entry directly?
            region_xywh = xywh_from_points(region.get_Coords().points)
            region_text = region.get_TextEquiv()
            if not region_text:
                LOG.warning("skipping empty text region %s", region.id)
                continue
            region_text = region_text[0].Unicode
            # FIXME: textual cues
            # FIXME: geometric rules
            if subtype in ['heading']:
                # FIXME: section vs article
                result.append([input_file, region.id, region_xywh, target, region_text])
            else:
                result.append([input_file, region.id, region_xywh, 'text', ''])
        return result

    def write_to_mets(self, results):  
        LOG = getLogger('OcrdDocStruct')
        mode = self.parameter['mode'] # enmap/mets:area or dfg/mets:structLink
        log_ids = sorted(int(id_[4:]) for id_ in self.log_ids
                         if id_[4:].isnumeric())
        if log_ids:
            last_id = log_ids[-1]
        else:
            last_id = 0
        def add_div(parent, div_type, text):
            nonlocal last_id
            last_id += 1
            div_id = "LOG_" + str(last_id)
            div = ET.SubElement(parent, TAG_METS_DIV)
            div.set('TYPE', div_type)            
            div.set('ID', div_id)
            if div_type != 'text':
                div.set('LABEL', text)
            self.log_map[div_id] = div
            self.log_ids.append(div_id)
            return div
        def add_link(page_id, div_id):
            # add mets:smLink entry to mets:structLink (for dfg representation)
            link = ET.SubElement(self.link, TAG_METS_SMLINK)
            link.set('{' + NS['xlink'] + '}to', page_id)
            link.set('{' + NS['xlink'] + '}from', div_id)
            self.link_map.setdefault(page_id, []).append(div_id)
            return link
        def add_area(parent, file_id, region_id):
            # add mets:fptr/mets:area entry to mets:div (for enmap representation)
            fptr = parent.find(TAG_METS_FPTR)
            if fptr is None:
                fptr = ET.SubElement(parent, TAG_METS_FPTR)
            if fptr.find(TAG_METS_SEQ):
                fptr = fptr.find(TAG_METS_SEQ)
            elif fptr.find(TAG_METS_AREA):
                area = fptr.find(TAG_METS_AREA)
                fptr.remove(area)
                fptr = ET.SubElement(fptr, TAG_METS_SEQ)
                fptr.append(area)
            area = ET.SubElement(fptr, TAG_METS_AREA)
            area.set('BETYPE', 'IDREF')
            area.set('FILEID', file_id)
            area.set('BEGIN', region_id)
            return area
        div = None
        last_type = None
        last_page = None
        for input_file, region_id, region_xywh, region_type, region_text in results:
            page_id = input_file.pageId
            if region_type == 'text':
                if div is None:
                    LOG.warning("%s: skipping region '%s' prior to first heading", page_id, region_id)
                    continue
                LOG.info("continuing with text region %s on page %s", region_id, page_id)
                if mode == 'enmap':
                    # add to current div
                    add_area(div, input_file.ID, region_id)
                else:
                    # extend current div's smlink to current page
                    loglist = self.link_map.get(page_id, [])
                    if not any(log == div.get('ID') for log in loglist):
                        add_link(page_id, div.get('ID'))
            else:
                if div is None:
                    loglist = self.link_map.get(page_id, [])
                    if len(loglist):
                        log = self.log_map[loglist[-1]]
                        LOG.info("starting at last existing div for page: %s[%s]", log.get('ID'), log.get('TYPE'))
                    else:
                        # get deepest embedded, still non-structural existing div
                        log = next([log for log in reversed(self.log.iterdescendants(TAG_METS_DIV))
                                    if log.get('TYPE').lower() in [
                                            # 'serial', 'multivolume_work', 'newspaper',
                                            'issue', # 'month', 'year', 
                                            'part', 'folder', 'map', 'illustration', 'additional',
                                            'volume', 'monograph', # 'chapter',
                                            'letter', 'fascicle', 'fragment', 'manuscript', 'bundle',
                                    ]], self.log)
                        LOG.info("starting at deepest existing div: %s[%s]", log.get('ID'), log.get('TYPE'))
                    div = log
                div_type = div.get('TYPE').lower()
                if (div_type in [
                        None, 'issue', 'part', 'folder', 'map', 'illustration', 'additional', 'title_page',
                        'volume', 'monograph', 'letter', 'fascicle', 'fragment', 'manuscript', 'bundle'] or
                    region_type in [
                        'index', 'table_of_contents', 'appendix', 'preface', 'dedication', 'privilege',
                        'review', 'musical_notation', 'bookplate', 'binding', 'address', 'annotation',
                        ] or
                    (div_type != region_type and region_type in ['article', 'verse', 'entry']) or 
                    (div_type == 'chapter' and region_type == 'section')):
                    # subordination
                    div = add_div(div, region_type, region_text)
                elif last_type == region_type:
                    # merge (follow-up heading without text)
                    div.set('LABEL', div.get('LABEL') + '\n' + region_text)
                else:
                    # coordination
                    div = add_div(div.getparent(), region_type, region_text)
                LOG.info("continuing with %s region %s on page %s", region_type, region_id, page_id)
                if mode == 'enmap':
                    # add to new div
                    add_area(div, input_file.ID, region_id)
                else:
                    # extend new div's smlink to current page
                    loglist = self.link_map.get(page_id, [])
                    if not any(log == div.get('ID') for log in loglist):
                        add_link(page_id, div.get('ID'))
            last_type = region_type
            last_page = page_id

@click.command()
@ocrd_cli_options
def cli(*args, **kwargs):
    return ocrd_cli_wrap_processor(OcrdDocStruct, *args, **kwargs)
