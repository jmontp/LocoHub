"""Artificial model XML only, no OpenSim import or coordinate evaluation."""
import pytest
from contributor_tools.inspect_mblue_orientation_model_xml import read_model,census,BODIES

def xml():
    bodies=''.join('<Body name="'+n+'"/>' for n in BODIES)
    return '<OpenSimDocument><Model><length_units>meters</length_units><force_units>N</force_units><gravity>0 -9.81 0</gravity><BodySet><objects>'+bodies+'</objects></BodySet><JointSet><objects><CustomJoint name="knee_r"><coordinates><Coordinate name="knee_angle_r"><locked>false</locked></Coordinate></coordinates><SpatialTransform><TransformAxis name="translation1"><coordinates>knee_angle_r</coordinates><axis>1 0 0</axis><MultiplierFunction><function><SimmSpline><x>0 1</x><y>0 2</y></SimmSpline></function></MultiplierFunction></TransformAxis></SpatialTransform></CustomJoint></objects></JointSet><MarkerSet><objects><Marker name="RHEEL"><socket_parent_frame>/bodyset/calcn_r</socket_parent_frame><location>-0.01 0.05 0</location></Marker></objects></MarkerSet></Model></OpenSimDocument>'

def test_literal_not_inferred_axes(tmp_path):
    p=tmp_path/'model.osim';p.write_text(xml());d=read_model(p)
    assert d['gravity']=='0 -9.81 0' and d['landmarks']['RHEEL']['location']=='-0.01 0.05 0'
    assert d['joints']['knee_r']['transform_axes'][0]['contains_spline'] is True
    assert 'anatomical_axis' not in d
    inventory={'records':[{'subject':'synthetic','date':'synthetic','models':[{'path':str(p),'sha256':d['sha256']}]}]}
    assert census(inventory)['model_count']==1
    p.write_text(xml().replace('0 -9.81 0','0 0 -9.81'))
    with pytest.raises(ValueError,match='changed'):census(inventory)

@pytest.mark.parametrize('mutation',['missing_body','duplicate_body','duplicate_coordinate'])
def test_ambiguous_model_structure_rejected(tmp_path,mutation):
    text=xml()
    if mutation=='missing_body':text=text.replace('<Body name="calcn_l"/>','')
    elif mutation=='duplicate_body':text=text.replace('</objects></BodySet>','<Body name="pelvis"/></objects></BodySet>')
    else:text=text.replace('</coordinates>','<Coordinate name="knee_angle_r"/></coordinates>',1)
    p=tmp_path/'model.osim';p.write_text(text)
    with pytest.raises(ValueError):read_model(p)


def test_read_is_bounded_even_without_size_precheck(tmp_path):
    from contributor_tools.inspect_mblue_orientation_model_xml import bounded_bytes
    p = tmp_path / 'growing-source'
    p.write_bytes(b'12345')
    assert bounded_bytes(p, 5) == b'12345'
    with pytest.raises(MemoryError):
        bounded_bytes(p, 4)
