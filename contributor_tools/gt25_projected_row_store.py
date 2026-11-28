"""Isolated bounded CSV projection proposal, not adopted by frozen converters.

Disk-backed float64 rows retain whole-trial absolute indices and source clocks.
No whole-recording arrays, concatenation, segmentation, or conversion occurs.
"""
import csv
import hashlib
import json
import math
from pathlib import Path
import struct

def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024**2),b''):h.update(chunk)
    return h.hexdigest()


CHUNK_ROWS=4096
MAX_WINDOW_ROWS=4096
MAX_LINE_BYTES=1024**2
MAX_COLUMNS=64


def projection(kind, transfer=False):
    joints=('hip_flexion','knee_angle','ankle_angle')
    if kind=='angle_filt':cols=[f'{joint}_{side}' for joint in joints for side in ('l','r')]
    elif kind in ('moment_filt','moment_filt_bio'):cols=[f'{joint}_{side}_moment' for joint in joints for side in ('l','r')]
    elif kind=='grf':cols=[f'fp_{side}_force_{axis}' for side in ('l','r') for axis in ('x','y','z')]
    elif kind=='velocity':cols=[f'{joint}_{side}_velocity' for joint in joints[:2] for side in ('l','r')]
    elif kind=='insole_sim':cols=[f'insole_{side}_cop_{axis}' for side in ('l','r') for axis in ('x','z')]
    elif kind=='exo':cols=[f'{joint}_{side}_torque_interaction' for joint in ('hip_angle','knee_angle') for side in ('l','r')]
    elif kind=='imu_sim':cols=[f'{body}_imu_{side}_{signal}' for body in ('thigh','shank','foot') for side in ('l','r') for signal in (('gyro_z','accel_x','accel_y') if transfer else ('gyro_z',))]
    elif kind in ('power','power_bio','exo_sim'):cols=[] # Legacy code checks these clocks but consumes no signal values.
    else:raise ValueError('Unknown source kind')
    return ['time',*cols]


def build(source, output, columns, *, guard=lambda:None, chunk_rows=CHUNK_ROWS):
    source=Path(source).resolve();output=Path(output).resolve()
    if not 1<=chunk_rows<=CHUNK_ROWS or not columns or len(columns)>MAX_COLUMNS or len(columns)!=len(set(columns)) or columns[0]!='time':
        raise ValueError('Invalid bounded projection')
    if output.exists():raise FileExistsError('Preserve existing row-store attempt')
    output.mkdir(parents=True,exist_ok=False)
    source_before=source.stat();sha=hashlib.sha256();row_sha=hashlib.sha256();count=0;previous=-math.inf
    pack=struct.Struct('<'+'d'*len(columns));partial=output/'rows.f64.partial'
    def lines(stream):
        while True:
            line=stream.readline(MAX_LINE_BYTES+1)
            if not line:break
            if len(line)>MAX_LINE_BYTES:raise ValueError('CSV line exceeds bounded admission')
            sha.update(line);yield line.decode('utf-8-sig' if stream.tell()==len(line) else 'utf-8')
    with source.open('rb') as stream,partial.open('xb') as target:
        reader=csv.reader(lines(stream));header=next(reader)
        if len(header)!=len(set(header)) or not set(columns)<=set(header):raise ValueError('Missing or duplicate source columns')
        indices=[header.index(c) for c in columns];buffer=bytearray()
        for row in reader:
            if len(row)!=len(header):raise ValueError('CSV row width differs')
            values=[float('nan') if row[i].strip().lower() in ('','nan','na','n/a') else float(row[i]) for i in indices]
            if not math.isfinite(values[0]) or values[0]<=previous:raise ValueError('Source clock not finite strictly increasing')
            previous=values[0];buffer.extend(pack.pack(*values));count+=1
            if count%chunk_rows==0:
                guard();target.write(buffer);row_sha.update(buffer);buffer.clear()
        if buffer:guard();target.write(buffer);row_sha.update(buffer)
    after=source.stat()
    if (source_before.st_size,source_before.st_mtime_ns)!=(after.st_size,after.st_mtime_ns):raise ValueError('Source changed during projection')
    if count<2:raise ValueError('Insufficient source rows')
    partial.rename(output/'rows.f64')
    metadata={'status':'projected_source_rows_unreviewed','scientific_approval':False,'source_path':str(source),
        'reader_sha256':digest(__file__), 'source_bytes':after.st_size,'source_sha256':sha.hexdigest(),'source_header':header,'columns':columns,'rows':count,
        'row_bytes':pack.size,'projected_bytes':count*pack.size,'projected_sha256':row_sha.hexdigest(),
        'source_index':'zero-based absolute CSV data row; header excluded','byte_order':'little-endian IEEE754 float64',
        'chunk_rows':chunk_rows,'maximum_read_window_rows':MAX_WINDOW_ROWS}
    (output/'metadata.json').write_text(json.dumps(metadata,indent=2)+'\n')
    return metadata


class Store:
    def __init__(self, path):
        self.path=Path(path);self.metadata=json.loads((self.path/'metadata.json').read_text())
        if self.metadata['status']!='projected_source_rows_unreviewed':raise ValueError('Incomplete store')
        self.columns=self.metadata['columns'];self.rows=self.metadata['rows'];self.pack=struct.Struct('<'+'d'*len(self.columns))
        if (self.path/'rows.f64').stat().st_size!=self.rows*self.pack.size:raise ValueError('Row-store length differs')
        if digest(self.path/'rows.f64')!=self.metadata['projected_sha256']:raise ValueError('Row-store hash differs')

    def window(self, start, end):
        if not 0<=start<=end<self.rows or end-start+1>MAX_WINDOW_ROWS:raise ValueError('Invalid or oversized inclusive source window')
        with (self.path/'rows.f64').open('rb') as stream:
            stream.seek(start*self.pack.size);data=stream.read((end-start+1)*self.pack.size)
        if len(data)!=(end-start+1)*self.pack.size:raise ValueError('Truncated source window')
        return list(self.pack.iter_unpack(data))

    def iter_rows(self, chunk_rows=CHUNK_ROWS):
        if not 1<=chunk_rows<=CHUNK_ROWS:raise ValueError('Invalid iteration chunk')
        for start in range(0,self.rows,chunk_rows):
            for offset,row in enumerate(self.window(start,min(self.rows-1,start+chunk_rows-1))):yield start+offset,row


def aligned_windows(stores, start, end):
    if len({store.rows for store in stores.values()})!=1:raise ValueError('Whole-trial source row counts differ')
    windows={kind:store.window(start,end) for kind,store in stores.items()}
    reference=next(iter(windows.values()))
    for rows in windows.values():
        if any(abs(a[0]-b[0])>1e-9 for a,b in zip(reference,rows)):raise ValueError('Source clocks differ')
    return windows
