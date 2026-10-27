"""Known two-foot geometry for the independent source readback."""
import importlib.util
from pathlib import Path
import numpy as np

path=Path(__file__).resolve().parents[1]/'contributor_tools/audit_probes/2026_10_20/check_gt21_force_outputs.py'
spec=importlib.util.spec_from_file_location('force_readback',path)
probe=importlib.util.module_from_spec(spec);spec.loader.exec_module(probe)


def sources():
    markers={'Header':np.arange(3.)};fp={'Header':np.arange(3.)}
    for leg,x in [('L',0.),('R',1000.)]:
        for point in ['Heel','Toe_Tip']:
            for axis in 'xyz':markers[f'{leg}_{point}_{axis}']=np.full(3,x if axis=='x' else 0.)
    for suffix,value in [('vx',0.),('vy',200.),('vz',0.),('px',.1),('py',0.),('pz',0.)]:fp['FP1_'+suffix]=np.full(3,value)
    return fp,markers


def test_known_left_contact_does_not_default_to_right():
    fp,markers=sources()
    assert probe.select_plate(fp,markers,0,2,'left','ramp')==('FP1',['FP1'])
    assert probe.select_plate(fp,markers,0,2,'right','ramp')==(None,[])


def test_exact_two_thirds_support_is_insufficient():
    fp,markers=sources();fp['FP1_px']=np.array([.1,.1,.9])
    assert probe.select_plate(fp,markers,0,2,'left','levelground')==(None,[])


def test_multiple_supported_plates_are_ambiguous():
    fp,markers=sources()
    for name,value in list(fp.items()):
        if name.startswith('FP1_'):fp[name.replace('FP1_','FP2_')]=value.copy()
    assert probe.select_plate(fp,markers,0,2,'left','stair')==(None,['FP1','FP2'])


def test_missing_contact_geometry_is_not_ignored():
    fp,markers=sources();markers['L_Heel_x'][1]=np.nan
    assert probe.select_plate(fp,markers,0,2,'left','ramp')==(None,[])


def test_threshold_and_equal_distance_do_not_establish_contact():
    fp,markers=sources();fp['FP1_vy'][:]=100
    assert probe.select_plate(fp,markers,0,2,'left','ramp')==(None,[])
    fp['FP1_vy'][:]=200;fp['FP1_px'][:]=.5
    assert probe.select_plate(fp,markers,0,2,'left','ramp')==(None,[])


def test_named_treadmill_plate_requires_complete_channels():
    fp,_=sources();fp={k.replace('FP1','Treadmill_R'):v for k,v in fp.items()}
    assert probe.select_plate(fp,{},0,2,'right','treadmill')==('Treadmill_R',['Treadmill_R'])
    del fp['Treadmill_R_pz']
    assert probe.select_plate(fp,{},0,2,'right','treadmill')==(None,[])
