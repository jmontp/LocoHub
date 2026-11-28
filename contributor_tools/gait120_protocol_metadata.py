"""Reported Gait120 apparatus dimensions, not per-recording measurements.

Source: Boo et al., Scientific Data 12,1023 (2025),
doi:10.1038/s41597-025-05391-0. Printed PDF pages2 and8.
"""
DOI = '10.1038/s41597-025-05391-0'


def protocol_metadata(task):
    """Return fresh task-specific metadata; never substitute mean walking speed."""
    if task in {'stair_ascent', 'stair_descent'}:
        values, page = {'step_height_m': 0.10}, 8
    elif task in {'incline_walking', 'decline_walking'}:
        values = {'incline_deg': 10.1 if task == 'incline_walking' else -10.1}
        page = 8
    elif task in {'sit_to_stand', 'stand_to_sit'}:
        values, page = {'seat_height_m': 0.490}, 2
    else:
        return {}
    return {**values, 'protocol_metadata_evidence': {
        'doi': DOI, 'pdf_page': page, 'scope': 'reported_experimental_apparatus',
        'fields': list(values),
    }}


def metadata_patch_proposal(source):
    """Patch only an isolated converter copy; fail if its reviewed shape changed."""
    import_anchor = 'import json\n'
    metadata_anchor = "    task_info_str = json.dumps({\n"
    if source.count(import_anchor) != 1 or source.count(metadata_anchor) != 1:
        raise ValueError('Converter source shape changed; review metadata insertion')
    source = source.replace(import_anchor, import_anchor+
        'from contributor_tools.gait120_protocol_metadata import protocol_metadata\n', 1)
    return source.replace(metadata_anchor, metadata_anchor+'        **protocol_metadata(task),\n', 1)
