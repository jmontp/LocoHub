"""Internal, fail-closed reader for the observed GT21 numeric MCOS table layout.

This is not a general MATLAB table reader. The exact single-table serialization
layout is admitted only after comparison with native MATLAB exports. Unknown
layouts, nonnumeric columns, or ambiguous objects require native MATLAB instead.
"""
import hashlib
import io
from pathlib import Path
import numpy as np
from scipy.io import loadmat
from scipy.io.matlab._mio5 import MatFile5Reader

SUPPORTED_LAYOUT_SHA256='45c5f9c2192e455b7a191cddb503fd3455ccd2b6904bc516c6cdce8056c0d3a1'


def numeric_columns(cells):
    if len(cells)!=11 or hashlib.sha256(cells[0].tobytes()).hexdigest()!=SUPPORTED_LAYOUT_SHA256:
        raise ValueError('Unsupported MCOS table layout; use native MATLAB')
    scalar=lambda value: float(np.asarray(value).item())
    if scalar(cells[3])!=2 or np.asarray(cells[5]).size:
        raise ValueError('Only two-dimensional tables without row names are supported')
    rows,columns=scalar(cells[4]),scalar(cells[6])
    if not rows.is_integer() or not columns.is_integer() or rows<1 or columns<1:
        raise ValueError('Invalid table dimensions')
    rows,columns=int(rows),int(columns)
    values=list(cells[2].flat);names=list(cells[7].flat)
    if len(values)!=columns or len(names)!=columns:raise ValueError('Table dimension mismatch')
    result={}
    for name,value in zip(names,values):
        if name.dtype.kind!='U' or name.size!=1:raise ValueError('Unsupported variable name encoding')
        name=str(name.item())
        if not name or name in result:raise ValueError('Empty or duplicate table variable')
        if value.dtype!=np.float64 or value.shape!=(rows,1):raise ValueError('Unsupported numeric column layout')
        result[name]=value[:,0]
    if 'Header' not in result:raise ValueError('Missing source clock')
    clock=result['Header']
    if not np.isfinite(clock).all() or not (np.diff(clock)>0).all():raise ValueError('Invalid source clock')
    return result


def read_numeric_table(path, max_source_bytes=64*1024**2):
    """Return original named float columns; never assign axes or change signs."""
    path=Path(path)
    if path.stat().st_size>max_source_bytes:raise MemoryError('MAT source exceeds bounded admission')
    source=loadmat(path)
    objects=[v for k,v in source.items() if not k.startswith('__')]
    if len(objects)!=1:raise ValueError('Expected exactly one source table')
    table=objects[0]
    if table.shape!=(1,) or table.dtype.names!=('s0','s1','s2','arr'):
        raise ValueError('Source is not the supported opaque table')
    if table['s0'][0]!=b'data' or table['s1'][0]!=b'MCOS' or table['s2'][0]!=b'table':
        raise ValueError('Unsupported source object class')
    if not np.array_equal(table['arr'][0].reshape(-1),[3707764736,2,1,1,1,1]):
        raise ValueError('Unsupported table object reference')
    workspace=source['__function_workspace__'].tobytes()
    if workspace[:8]!=b'\x00\x01IM\x00\x00\x00\x00':raise ValueError('Unsupported workspace header')
    # Embedded MAT streams lack the descriptive 124-byte file header. Keep the
    # original version/endian bytes. Read variables sequentially: both embedded
    # variables are unnamed, so loadmat's name-keyed dictionary loses the first.
    reader=MatFile5Reader(io.BytesIO(b' '*124+workspace[:4]+workspace[8:]))
    reader.initialize_read();reader.read_file_header()
    header,next_position=reader.read_var_header()
    if header.name!=b'' or header.mclass!=2:raise ValueError('Unsupported workspace root')
    root=reader.read_var_array(header,process=True)
    if root.shape!=(1,1) or root.dtype.names!=('MCOS',):raise ValueError('Ambiguous workspace root')
    wrapper=root['MCOS'][0,0]
    if wrapper.shape!=(1,) or wrapper['s1'][0]!=b'MCOS' or wrapper['s2'][0]!=b'FileWrapper__':
        raise ValueError('Unsupported workspace wrapper')
    result=numeric_columns(wrapper['arr'][0].reshape(-1))
    reader.mat_stream.seek(next_position)
    tail_header,tail_end=reader.read_var_header()
    tail=reader.read_var_array(tail_header,process=True)
    if tail_header.name!=b'' or tail.dtype!=np.uint8 or tail.shape!=(1,88):
        raise ValueError('Unsupported workspace footer')
    reader.mat_stream.seek(tail_end)
    if not reader.end_of_stream():raise ValueError('Unexpected extra workspace objects')
    return result
