"""Stdlib structure and halo fixtures; no real numerical execution."""
import ast
from pathlib import Path
import unittest
from contributor_tools.run_gt24_continuous_pilot_v2 import allowed_changes,added_fields,source_columns
from contributor_tools.run_gt24_continuous_pilot import manual_derivative


class StreamingAuditTests(unittest.TestCase):
    def test_precise_allowlist_cannot_hide_segment_changes(self):
        changed=allowed_changes()
        for segment in ('thigh','shank','foot'):
            for role in ('ipsi','contra'):
                for kind,unit in [('angle','rad'),('velocity','rad_s'),('acceleration','rad_s2')]:
                    self.assertNotIn(f'{segment}_sagittal_{kind}_{role}_{unit}',changed)
        self.assertNotIn('unexpected_velocity_ipsi_rad_s',changed)
        self.assertIn('knee_flexion_velocity_ipsi_rad_s',changed)
        self.assertIn('ankle_dorsiflexion_moment_contra_Nm_kg',changed)

    def test_source_fields_and_additions_are_explicit(self):
        self.assertEqual(len(added_fields()),21)
        columns=source_columns()
        self.assertEqual(columns['angle_filt'],{'time',*[f'{joint}_{side}' for joint in ('hip_flexion','knee_angle','ankle_angle') for side in ('l','r')]})
        self.assertNotIn('unrequested',set().union(*columns.values()))

    def test_two_row_halos_preserve_nested_derivatives(self):
        times=[float(i*i+i)/100 for i in range(20)];angles=[2*t*t-3*t+4 for t in times]
        full=manual_derivative(manual_derivative(angles,times),times)
        collected=[]
        for start in range(0,len(times),5):
            stop=min(len(times),start+5);lo=max(0,start-2);hi=min(len(times),stop+2)
            partial=manual_derivative(manual_derivative(angles[lo:hi],times[lo:hi]),times[lo:hi])
            collected.extend(partial[start-lo:stop-lo])
        self.assertEqual(collected,full)

    def test_audit_uses_parquet_batches_not_dataset_loader(self):
        source=Path('contributor_tools/run_gt24_continuous_pilot_v2.py').read_text();tree=ast.parse(source)
        calls=[n for n in ast.walk(tree) if isinstance(n,ast.Call)]
        self.assertFalse(any(isinstance(n.func,ast.Attribute) and n.func.attr=='read_table' for n in calls))
        self.assertIn('iter_batches(batch_size=512,use_threads=False)',source)
        self.assertIn('nrows=20001',source)

    def test_persisted_segment_or_unexpected_field_mutation_rejected(self):
        from contributor_tools.run_gt24_continuous_pilot_v2 import check_unmodified
        class Field:
            def __init__(self,name):self.name=name
            def equals(self,other,check_metadata=False):return self.name==other.name
        class Array:
            def __init__(self,values):self.values=values
            def to_pylist(self):return self.values
            def is_null(self):return Array([x is None for x in self.values])
            def equals(self,other):return self.values==other.values
        class Schema:
            def __init__(self,names):self.names=names
            def get_field_index(self,name):return self.names.index(name)
            def field(self,name):return Field(name)
        class Batch:
            def __init__(self,data):self.data=data;self.schema=Schema(list(data))
            def column(self,index):return Array(self.data[self.schema.names[index]])
        original={'shank_sagittal_velocity_ipsi_rad_s':[2.,None],'unexpected_feature':[5.,6.],'ankle_dorsiflexion_angle_ipsi_rad':[1.,2.]}
        corrected={**original,**{k:[None,None] for k in added_fields()}}
        corrected['ankle_dorsiflexion_angle_ipsi_rad']=[-1.,-2.]
        check_unmodified(Batch(original),Batch(corrected))
        for name in ['shank_sagittal_velocity_ipsi_rad_s','unexpected_feature']:
            bad={**corrected,name:[999.,None]}
            with self.assertRaisesRegex(ValueError,'Unmodified'):check_unmodified(Batch(original),Batch(bad))
