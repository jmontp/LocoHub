"""Bounded Complete/Parsed membership primitives. No data execution on import.

Scan a native ZIP member directly, retaining only one row from each source.
Membership requires exact absolute timestamps and declared projected values;
name prefixes alone never establish membership. Unmatched rows remain explicit.
"""
import csv
import hashlib
import math
import struct


class ProjectedCSV:
    def __init__(self, stream, columns, guard=lambda: None, max_bytes=2**34):
        self.columns = tuple(columns)
        if not self.columns or 'time' not in self.columns or len(set(self.columns)) != len(self.columns):
            raise ValueError('Unique projected fields including time required')
        self.guard = guard
        self.sha = hashlib.sha256()
        self.clock_sha = hashlib.sha256()
        self.bytes = 0
        self.rows = 0
        self.previous = -math.inf
        self.complete = False
        def lines():
            while True:
                guard()
                line = stream.readline(65537)
                if not line:
                    self.complete = True
                    break
                self.bytes += len(line)
                if len(line) > 65536 or self.bytes > max_bytes:
                    raise ValueError('Source CSV byte admission exceeded')
                self.sha.update(line)
                yield line.decode('utf-8-sig')
        self.reader = csv.DictReader(lines())
        fields = self.reader.fieldnames
        if not fields or len(fields) != len(set(fields)) or not set(columns) <= set(fields):
            raise ValueError('Required source fields absent or duplicated')

    def __iter__(self):
        return self

    def __next__(self):
        row = next(self.reader)
        if None in row or any(value is None for value in row.values()):
            raise ValueError('Malformed source CSV row')
        values = {name: float(row[name]) for name in self.columns}
        clock = values['time']
        if not math.isfinite(clock) or clock <= self.previous:
            raise ValueError('Clock must be finite and strictly increasing')
        if any(math.isinf(value) for value in values.values()):
            raise ValueError('Infinite source measurement')
        self.clock_sha.update(struct.pack('>d', clock))
        self.previous = clock
        self.rows += 1
        return values

    def evidence(self):
        if not self.complete:
            raise ValueError('Cannot claim complete source identity before EOF')
        return {'full_csv_sha256': self.sha.hexdigest(), 'bytes': self.bytes,
                'rows': self.rows, 'clock_sha256': self.clock_sha.hexdigest(), 'projected_fields': list(self.columns)}


class Runs:
    """Bounded run-length ledger: inclusive row indices and exact source clocks."""
    def __init__(self, limit=10000):
        self.items = []
        self.limit = limit

    def add(self, index, clock):
        if self.items and index == self.items[-1]['last_row'] + 1:
            self.items[-1].update(last_row=index, last_time_s=clock)
        else:
            if len(self.items) >= self.limit:
                raise ValueError('Interval ledger admission exceeded')
            self.items.append({'first_row': index, 'last_row': index,
                               'first_time_s': clock, 'last_time_s': clock})


def compare_membership(native, parsed, max_intervals=10000):
    """Consume both streams completely, returning evidence even for false candidates.

    Numeric tolerance matches the executed native/Parsed pilot; timestamps must
    match exactly. A true result proves only this projected table membership.
    """
    if native.columns != parsed.columns:
        raise ValueError('Source projections differ')
    columns = [name for name in native.columns if name != 'time']
    finite = dict.fromkeys(columns, 0)
    missing = dict.fromkeys(columns, 0)
    matches, uncovered = Runs(max_intervals), Runs(max_intervals)
    absent, differing = 0, 0
    pending = next(parsed, None)
    for index, source in enumerate(native):
        while pending is not None and pending['time'] < source['time']:
            absent += 1
            pending = next(parsed, None)
        matched = False
        if pending is not None and pending['time'] == source['time']:
            same = True
            for name in columns:
                a, b = source[name], pending[name]
                if math.isnan(a) != math.isnan(b):
                    same = False
                elif math.isnan(a):
                    missing[name] += 1
                elif not math.isclose(a, b, rel_tol=1e-10, abs_tol=1e-9):
                    same = False
                else:
                    finite[name] += 1
            if same:
                matched = True
                matches.add(index, source['time'])
            else:
                differing += 1
            pending = next(parsed, None)
        if not matched:
            uncovered.add(index, source['time'])
    while pending is not None:
        absent += 1
        pending = next(parsed, None)
    native_evidence, parsed_evidence = native.evidence(), parsed.evidence()
    if native.rows == 0 or parsed.rows == 0:
        raise ValueError('Empty source is not positive membership evidence')
    passed = absent == 0 and differing == 0
    return {'status': 'projected_table_membership_checked_unreviewed' if passed else 'candidate_membership_rejected',
            'membership_verified': passed, 'native': native_evidence, 'parsed': parsed_evidence,
            'parsed_clocks_absent': absent, 'parsed_rows_with_different_values': differing,
            'matched_native_intervals': matches.items,
            'native_intervals_not_matched_to_this_candidate': uncovered.items,
            'finite_equal_values': finite, 'missing_equal_values_unassessed': missing,
            'scope': 'One candidate and declared projected fields only; not whole native coverage or anatomical verification'}


def require_shared_membership(tables):
    """No recording-level success unless every required table proves same row clocks."""
    if not tables:
        raise ValueError('No source table evidence')
    first = next(iter(tables.values()))
    for result in tables.values():
        if not result['membership_verified']:
            raise ValueError('Candidate source membership unresolved')
        if result['matched_native_intervals'] != first['matched_native_intervals']:
            raise ValueError('Source table matched intervals differ')
        if any(result[scope]['clock_sha256'] != first[scope]['clock_sha256'] for scope in ('native', 'parsed')):
            raise ValueError('Source table full clocks differ')
        if result['native']['rows'] != first['native']['rows'] or result['parsed']['rows'] != first['parsed']['rows']:
            raise ValueError('Source table row coverage differs')
    return first['matched_native_intervals']
