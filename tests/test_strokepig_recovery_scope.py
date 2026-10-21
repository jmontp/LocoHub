import pytest
from contributor_tools.check_strokepig_native_recovery import scope


def fixture():
 rows=[{'source_recording':f'walking/{i}.c3d','kind':'walking'} for i in range(151)]+[{'source_recording':f'calibration/{i}.c3d','kind':'calibration'} for i in range(49)]
 return {'c3d_sources':rows},{'status':'source_census_complete_unreviewed','records':[{'source_recording':r['source_recording'],'status':'inventoried'} for r in rows if r['kind']=='walking']}


def test_all_walking_and_calibration_accounted():
 walking,calibration=scope(*fixture());assert len(walking)==151 and len(calibration)==49 and not set(walking)&set(calibration)


@pytest.mark.parametrize('bad',['missing','duplicate','calibration_as_walking','unknown_role','census_duplicate','unresolved'])
def test_scope_fail_closed(bad):
 inventory,census=fixture()
 if bad=='missing':inventory['c3d_sources'].pop()
 elif bad=='duplicate':inventory['c3d_sources'][-1]=inventory['c3d_sources'][0]
 elif bad=='calibration_as_walking':inventory['c3d_sources'][-1]['kind']='walking'
 elif bad=='unknown_role':inventory['c3d_sources'][-1]['kind']='unknown'
 elif bad=='census_duplicate':census['records'][-1]=census['records'][0]
 else:census['records'][0]['status']='failed'
 with pytest.raises(ValueError):scope(inventory,census)


def linked_fixture():
 record={'rows':150,'output_sha256':'out','components_checked':12}
 metadata={'rows':150,'source_sha256':'source','output_sha256':'out','converter_sha256':'converter'}
 comparison={'status':'exact_source_companion_readback','scientific_approval':False,'rows':150,'source_sha256':'source','output_sha256':'out','probe_sha256':'probe','components_and_residuals_checked':12}
 return record,metadata,comparison,{'sha256':'source'},'out','probe','converter'


def test_linked_readback_receipt():
 from contributor_tools.check_strokepig_native_recovery import record_links
 record_links(*linked_fixture())


@pytest.mark.parametrize('field,value',[('rows',149),('source_sha256','wrong'),('output_sha256','wrong'),('probe_sha256','wrong'),('components_and_residuals_checked',0),('components_and_residuals_checked',11),('scientific_approval',True)])
def test_malformed_readback_cannot_pass(field,value):
 from contributor_tools.check_strokepig_native_recovery import record_links
 args=list(linked_fixture());args[2][field]=value
 with pytest.raises(ValueError):record_links(*args)
