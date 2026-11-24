"""Independent re-derivation for one GT21 recording. Source access uses the repo's table reader only (data access).
All maths below is written separately from the worker's pass."""
import sys, json, math, re, resource, faulthandler; faulthandler.dump_traceback_later(300, exit=True)
import numpy as np, time
T0=time.time()
def lg(m): print(m, round(time.time()-T0,1), file=sys.stderr, flush=True)
import xml.etree.ElementTree as ET
sys.path.insert(0, '/mnt/s/workspace/locomotion-data-standardization')
from contributor_tools import gt21_numeric_source as reader   # data access only
import pyarrow.parquet as pq
REPO = '/mnt/s/workspace/locomotion-data-standardization/'
BASES = {'local_2024_copy_bundle': REPO + 'contributor_tools/conversion_scripts/Gtech_2021/CAMARGO_ET_AL_J_BIOMECH_DATASET/',
         'extracted_2024_copy_zip': '/mnt/s/locomotion_data/gt21_author_mirror_2024_extracted/'}
OUT = REPO + 'converted_datasets/reconversion_v2/gt21_rb_pass_batch_%s_20261124/'
UP = np.array([0., 1., 0.])

subject, source, session, mode, rec = json.loads(sys.argv[1])
base = BASES[source] + subject + '/'
tab = {}
def rd_ch(ch):
    try: tab[ch] = reader.read_numeric_table(f'{base}{session}/{mode}/{ch}/{rec}.mat')
    except Exception as e: tab[ch] = None; print('read fail', ch, e, file=sys.stderr)
rd_ch('markers')
mk = tab['markers']; t = np.asarray(mk['Header']); n = len(t)
need = [k[:-2] for k in mk if k.endswith('_x') and k[:-2]+'_y' in mk and k[:-2]+'_z' in mk]
P = {m: np.stack([mk[m+'_x'], mk[m+'_y'], mk[m+'_z']], 1) / 1000. for m in need}
del tab['markers'], mk
stored = pq.read_table(OUT % subject + f'{subject}/{mode}/{rec}.parquet').to_pandas()
assert len(stored) == n, (len(stored), n)
res = {'recording': f'{subject}/{mode}/{rec}', 'n': n, 'time_max_diff': float(np.abs(stored.time_s.values - t).max())}

lg('loaded')
# ---- weight
info = json.load(open(REPO + 'converted_datasets/reconversion_v2/gt21_rb01_labels_final_20261124/%s/subject_info_%s.json' % (subject, subject)))
W = float(info['values']['Weight']); assert info['variable_units'][info['variable_names'].index('Weight')] == 'kg'
BW = W * 9.81; res['weight_kg'] = W

# ---- pelvis
am = (P['L_ASIS'] + P['R_ASIS']) / 2; pm = (P['L_PSIS'] + P['R_PSIS']) / 2
d = am - pm; dh = d * np.array([1, 0, 1.]); fwdp = dh / np.linalg.norm(dh, axis=1)[:, None]
pelv = np.arctan2(d[:, 1], np.sum(d * fwdp, 1))
dp = np.abs(pelv - stored.pelvis_sagittal_angle_rad.values); res['pelvis_max_diff_rad'] = float(np.nanmax(dp)); res['pelvis_nan_mismatch'] = int((np.isnan(pelv) != stored.pelvis_sagittal_angle_rad.isna().values).sum())
res['pelvis_forward_xz_max_diff'] = float(max(np.nanmax(np.abs(fwdp[:, 0] - stored.pelvis_forward_lab_x.values)), np.nanmax(np.abs(fwdp[:, 2] - stored.pelvis_forward_lab_z.values))))
right_ref = np.cross(fwdp, UP)

lg('pelvis')
# ---- model (own parse)
def vec(s): return np.array(s.split(), float)
root = ET.parse(base + 'osimxml/%s.osim' % subject).getroot()
mkr = {}
for m in root.iter('Marker'):
    mkr[m.get('name')] = (m.findtext('socket_parent_frame').split('/')[-1], vec(m.findtext('location')))
J = {}
for j in root.iter('CustomJoint'):
    fr = {f.get('name'): (f.findtext('socket_parent').split('/')[-1], vec(f.findtext('translation')), vec(f.findtext('orientation'))) for f in j.iter('PhysicalOffsetFrame')}
    pf, cf = fr[j.findtext('socket_parent_frame')], fr[j.findtext('socket_child_frame')]
    rots = {}
    for ta in j.iter('TransformAxis'):
        if ta.get('name').startswith('rotation') and ta.findtext('coordinates').strip():
            rots[ta.findtext('coordinates').strip()] = vec(ta.findtext('axis'))
    J[j.get('name')] = dict(p=pf, c=cf, rots=rots)

def horn(local, meas):
    """Horn's quaternion fit, batch. local (k,3), meas (n,k,3) -> R (n,3,3), t (n,3), rms (n,)."""
    nn = len(meas); R = np.full((nn, 3, 3), np.nan); tt = np.full((nn, 3), np.nan); rms = np.full(nn, np.nan)
    ok = np.isfinite(meas).all((1, 2))
    if not ok.any(): return R, tt, rms
    m = meas[ok]; lc = local.mean(0); mc = m.mean(1)
    a = local - lc; b = m - mc[:, None, :]
    S = np.einsum('ki,nkj->nij', a, b)   # sum a_i b_j
    Sxx, Sxy, Sxz, Syx, Syy, Syz, Szx, Szy, Szz = [S[:, i, j] for i in range(3) for j in range(3)]
    N = np.zeros((len(m), 4, 4))
    N[:, 0, 0] = Sxx + Syy + Szz; N[:, 0, 1] = N[:, 1, 0] = Syz - Szy; N[:, 0, 2] = N[:, 2, 0] = Szx - Sxz; N[:, 0, 3] = N[:, 3, 0] = Sxy - Syx
    N[:, 1, 1] = Sxx - Syy - Szz; N[:, 1, 2] = N[:, 2, 1] = Sxy + Syx; N[:, 1, 3] = N[:, 3, 1] = Szx + Sxz
    N[:, 2, 2] = -Sxx + Syy - Szz; N[:, 2, 3] = N[:, 3, 2] = Syz + Szy; N[:, 3, 3] = -Sxx - Syy + Szz
    w, v = np.linalg.eigh(N); q = v[:, :, -1]; q0, q1, q2, q3 = q[:, 0], q[:, 1], q[:, 2], q[:, 3]
    Rk = np.stack([np.stack([q0*q0+q1*q1-q2*q2-q3*q3, 2*(q1*q2-q0*q3), 2*(q1*q3+q0*q2)], 1),
                   np.stack([2*(q1*q2+q0*q3), q0*q0-q1*q1+q2*q2-q3*q3, 2*(q2*q3-q0*q1)], 1),
                   np.stack([2*(q1*q3-q0*q2), 2*(q2*q3+q0*q1), q0*q0-q1*q1-q2*q2+q3*q3]) .T if False else np.stack([2*(q1*q3-q0*q2), 2*(q2*q3+q0*q1), q0*q0-q1*q1-q2*q2+q3*q3], 1)], 1)
    tk = mc - np.einsum('nij,j->ni', Rk, lc)
    r = np.sqrt(((np.einsum('nij,kj->nki', Rk, local) + tk[:, None, :] - m) ** 2).sum(2).mean(1))
    R[ok], tt[ok], rms[ok] = Rk, tk, r
    return R, tt, rms

def euler_R(o):
    ax, ay, az = o
    rx = np.array([[1,0,0],[0,math.cos(ax),-math.sin(ax)],[0,math.sin(ax),math.cos(ax)]])
    ry = np.array([[math.cos(ay),0,math.sin(ay)],[0,1,0],[-math.sin(ay),0,math.cos(ay)]])
    rz = np.array([[math.cos(az),-math.sin(az),0],[math.sin(az),math.cos(az),0],[0,0,1]])
    return rx @ ry @ rz

def fitset(body, names):
    use = [x for x in names if x in P and x in mkr and mkr[x][0] == body]
    return use, np.array([mkr[x][1] for x in use])

def chunks(k=1000):
    for a in range(0, n, k): yield slice(a, min(n, a+k))

def wrap(a): return (a + np.pi) % (2*np.pi) - np.pi
lg('model')
leg_out = {}
for leg, S, s in (('right', 'R', 'r'), ('left', 'L', 'l')):
    hip, knee, ank = J[f'hip_{s}'], J[f'knee_{s}'], J[f'ankle_{s}']
    assert hip['p'][0] == 'pelvis' and hip['c'][0] == f'femur_{s}' and np.allclose(hip['c'][1], 0), 'hip child offset'
    assert knee['p'][0] == f'femur_{s}' and knee['c'][0] == f'tibia_{s}' and np.allclose(knee['p'][1], 0) and np.allclose(knee['c'][1], 0)
    assert np.allclose(knee['p'][2], 0) and np.allclose(knee['c'][2], 0)
    axis_fem = knee['rots'][f'knee_angle_{s}']; axis_fem = axis_fem / np.linalg.norm(axis_fem)
    hip_loc = hip['p'][1]; ankle_loc = ank['p'][1]; assert ank['p'][0] == f'tibia_{s}'
    nm_p, lp = fitset('pelvis', ['L_ASIS', 'R_ASIS', 'L_PSIS', 'R_PSIS'])
    nm_f, lf = fitset(f'femur_{s}', [f'{S}_{x}' for x in ('Thigh_Upper', 'Thigh_Front', 'Thigh_Rear', 'Knee_Lat')])
    nm_t, lt = fitset(f'tibia_{s}', [f'{S}_{x}' for x in ('Shank_Upper', 'Shank_Front', 'Shank_Rear', 'Ankle_Lat')])
    if len(nm_f) < 3 or len(nm_t) < 3 or len(nm_p) < 3:
        leg_out[leg] = {'excluded': (nm_p, nm_f, nm_t)}; continue
    # also list every model marker on the body present in data (to check cluster filter loses nothing)
    allf = [x for x in P if x in mkr and mkr[x][0] == f'femur_{s}']; allt = [x for x in P if x in mkr and mkr[x][0] == f'tibia_{s}']
    H = np.full((n, 3), np.nan); K = H.copy(); A = H.copy(); AX = H.copy()
    rp = np.full(n, np.nan); rf = rp.copy(); rt = rp.copy()
    for sl in chunks():
        Rp, tp, a1 = horn(lp, np.stack([P[x][sl] for x in nm_p], 1))
        Rf, tf, a2 = horn(lf, np.stack([P[x][sl] for x in nm_f], 1))
        Rt, tt_, a3 = horn(lt, np.stack([P[x][sl] for x in nm_t], 1))
        H[sl] = tp + np.einsum('nij,j->ni', Rp, hip_loc)
        K[sl] = tt_                                            # knee child frame origin = tibia body origin (offset 0, checked)
        A[sl] = tt_ + np.einsum('nij,j->ni', Rt, ankle_loc)
        AX[sl] = np.einsum('nij,j->ni', Rf, axis_fem)
        rp[sl], rf[sl], rt[sl] = a1, a2, a3
    sgn = np.sign(np.sum(AX * right_ref, 1)); axr = AX * sgn[:, None]
    ah = axr * np.array([1, 0, 1.]); fwd = np.cross(UP, ah); fwd /= np.linalg.norm(fwd, axis=1)[:, None]
    def fu(v): return np.stack([np.sum(v * fwd, 1), v[:, 1]], 1)
    th = fu(K - H); sh = fu(A - K); ft = fu(P[f'{S}_Toe_Tip'] - P[f'{S}_Heel'])
    thigh = np.arctan2(th[:, 0], -th[:, 1]); shank = np.arctan2(sh[:, 0], -sh[:, 1]); foot = np.arctan2(ft[:, 1], ft[:, 0])
    # axis vs lateral knee marker
    thu = (K - H); thu /= np.linalg.norm(thu, axis=1)[:, None]
    dd = P[f'{S}_Knee_Lat'] - K; dd = dd - np.sum(dd * thu, 1)[:, None] * thu
    aa = axr - np.sum(axr * thu, 1)[:, None] * thu
    if leg == 'left': dd = -dd
    cosang = np.sum(dd * aa, 1) / (np.linalg.norm(dd, axis=1) * np.linalg.norm(aa, axis=1)); axang = np.degrees(np.arccos(np.clip(cosang, -1, 1)))
    with np.errstate(invalid='ignore'):
        hold_res = (rp > .02) | (rf > .02) | (rt > .02); hold_ax = axang > 45
    code = hold_res.astype(int) + 2 * hold_ax.astype(int)
    held = code > 0
    leg_out[leg] = dict(H=H, K=K, A=A, fwd=fwd, thigh=thigh, shank=shank, foot=foot, code=code, held=held, rp=rp, rf=rf, rt=rt, axang=axang,
                        extra_f=sorted(set(allf) - set(nm_f)), extra_t=sorted(set(allt) - set(nm_t)))
    lg('fit '+leg)
    # compare
    r = {'fit_markers': (nm_p, nm_f, nm_t), 'markers_on_body_not_in_cluster': (leg_out[leg]['extra_f'], leg_out[leg]['extra_t'])}
    r['hold_code_equal_frames'] = int((code == stored[f'geometry_hold_{leg}'].values).sum()); r['hold_code_total'] = n
    r['hold_mine'] = int(held.sum()); r['hold_stored'] = int((stored[f'geometry_hold_{leg}'].values > 0).sum())
    r['hold_pct_mine'] = float(100 * held.mean())
    r['hold_by_res'] = int(hold_res.sum()); r['hold_by_axis'] = int(hold_ax.sum())
    r['resid_mm_median'] = {k: float(np.nanmedian(v) * 1000) for k, v in (('pelvis', rp), ('femur', rf), ('tibia', rt))}
    r['resid_mm_p95'] = {k: float(np.nanpercentile(v, 95) * 1000) for k, v in (('pelvis', rp), ('femur', rf), ('tibia', rt))}
    r['axis_deg_median_p95'] = [float(np.nanmedian(axang)), float(np.nanpercentile(axang, 95))]
    ang = {}
    ang['thigh'], ang['shank'], ang['foot'] = [np.where(held, np.nan, v) for v in (thigh, shank, foot)]
    ang['hip'] = ang['thigh'] - pelv; ang['knee'] = ang['thigh'] - ang['shank']; ang['ankle'] = ang['foot'] - ang['shank']
    for k, col in (('thigh', f'thigh_sagittal_angle_{leg}_rad'), ('shank', f'shank_sagittal_angle_{leg}_rad'), ('foot', f'foot_sagittal_angle_{leg}_rad'),
                   ('hip', f'hip_flexion_angle_{leg}_rad'), ('knee', f'knee_flexion_angle_{leg}_rad'), ('ankle', f'ankle_dorsiflexion_angle_{leg}_rad')):
        sv = stored[col].values; both = np.isfinite(sv) & np.isfinite(ang[k])
        r[f'ang_{k}'] = {'both_finite': int(both.sum()), 'finite_mismatch': int((np.isfinite(sv) != np.isfinite(ang[k])).sum()),
                         'max_abs_diff_rad': float(np.abs(sv[both] - ang[k][both]).max()) if both.any() else None,
                         'p99_abs_diff_rad': float(np.percentile(np.abs(sv[both] - ang[k][both]), 99)) if both.any() else None}
    for k, col in (('hip', f'hip_flexion_velocity_{leg}_rad_s'), ('knee', f'knee_flexion_velocity_{leg}_rad_s'), ('ankle', f'ankle_dorsiflexion_velocity_{leg}_rad_s')):
        v = np.full(n, np.nan); v[1:-1] = wrap(ang[k][2:] - ang[k][:-2]) / (t[2:] - t[:-2]); v = np.where(held, np.nan, v)
        sv = stored[col].values; both = np.isfinite(sv) & np.isfinite(v)
        r[f'vel_{k}'] = {'both_finite': int(both.sum()), 'finite_mismatch': int((np.isfinite(sv) != np.isfinite(v)).sum()),
                         'max_abs_diff': float(np.abs(sv[both] - v[both]).max()) if both.any() else None}
    # plane forward: horizontal, perpendicular to axis
    r['fwd_horizontal_and_perp_axis_max'] = float(np.nanmax(np.abs(np.sum(fwd * axr, 1))))
    r['ankle_height_stats_m'] = None
    # composition check of stored
    r['composition_max'] = float(np.nanmax(np.abs(stored[f'hip_flexion_angle_{leg}_rad'] - (stored[f'thigh_sagittal_angle_{leg}_rad'] - stored.pelvis_sagittal_angle_rad))))
    leg_out[leg]['r'] = r; leg_out[leg]['ang'] = ang
res['legs'] = {l: leg_out[l].get('r', leg_out[l]) for l in leg_out}

lg('legs')
for _c in ('fp','gcLeft','gcRight'): rd_ch(_c)
# ---- plates
fp = tab['fp']
if fp is not None:
    ft_ = np.asarray(fp['Header']); pref = [c[:-3] for c in fp if c.endswith('_vy') and all(f'{c[:-3]}_{k}' in fp for k in ('vx','vz','px','py','pz'))]
    res['plates'] = pref
    def to_clock(x):
        out = np.full(n, np.nan); ins = (t >= ft_[0]) & (t <= ft_[-1]); out[ins] = np.interp(t[ins], ft_, x); return out
    plates = []
    for p in pref:
        vy_s = np.asarray(fp[p+'_vy']); loaded_s = np.nan_to_num(vy_s) > 1.0
        cop = np.stack([fp[p+'_px'], fp[p+'_py'], fp[p+'_pz']], 1)
        okc = loaded_s & np.isfinite(cop).all(1)
        j = np.clip(np.searchsorted(ft_, t, side='right') - 1, 0, len(ft_) - 2)
        ins = (t >= ft_[0]) & (t <= ft_[-1]); ongrid = ins & (ft_[j] == t)
        both = ins & okc[j] & (okc[j+1] | ongrid)
        c3 = np.full((n, 3), np.nan)
        for k in range(3):
            v = to_clock(np.where(okc, cop[:, k], np.nan)); c3[both, k] = v[both]
        plates.append(dict(name=p, vx=to_clock(np.asarray(fp[p+'_vx'])), vy=to_clock(vy_s), vz=to_clock(np.asarray(fp[p+'_vz'])), cop=c3))
    del fp; tab['fp'] = None; import gc as _gc; _gc.collect()
    gcs = {'left': tab['gcLeft'], 'right': tab['gcRight']}
    def events(gc):
        if gc is None: return None
        h = np.asarray(gc['Header']); out = []
        for c in ('HeelStrike', 'ToeOff'):
            x = np.asarray(gc[c]); tm = h[np.flatnonzero(np.diff(x) < -50) + 1]
            idx = np.array([int(np.argmin(np.abs(t - q))) for q in tm], int)
            ok = np.array([abs(t[i] - q) <= 0.5 * 0.005 + 1e-9 for i, q in zip(idx, tm)], bool) if len(idx) else np.zeros(0, bool)
            out.append(np.unique(idx[ok]))
        return out
    stance = {}
    for leg in ('right', 'left'):
        e = events(gcs[leg])
        if e is None or not (len(e[0]) or len(e[1])): stance[leg] = None; continue
        hs, to = np.sort(e[0]), np.sort(e[1]); m = np.zeros(n, bool)
        if len(to) and (not len(hs) or to[0] < hs[0]): m[:to[0]] = True
        for h_ in hs:
            k = np.searchsorted(to, h_, side='right'); m[h_: (to[k] if k < len(to) else n)] = True
        stance[leg] = m
    owner = {l: np.zeros((n, len(plates)), bool) for l in ('right', 'left')}
    cont = []
    if mode == 'treadmill':
        for i, p in enumerate(plates):
            if p['name'] == 'Treadmill_R': owner['right'][:, i] = True
            if p['name'] == 'Treadmill_L': owner['left'][:, i] = True
    else:
        mid = {l: (P[S+'_Heel'] + P[S+'_Toe_Tip']) / 2 for l, S in (('right', 'R'), ('left', 'L'))}
        for i, p in enumerate(plates):
            vy = np.nan_to_num(p['vy']); on = vy > 1.0
            runs = []; k = 0
            while k < n:
                if on[k]:
                    a = k
                    while k < n and on[k]: k += 1
                    runs.append([a, k])
                else: k += 1
            merged = []
            for a, b in runs:
                if merged and a - merged[-1][1] <= 4: merged[-1][1] = b
                else: merged.append([a, b])
            for a, b in merged:
                if not (vy[a:b] > 50).any(): continue
                dr = np.linalg.norm(p['cop'][a:b] - mid['right'][a:b], axis=1); dl = np.linalg.norm(p['cop'][a:b] - mid['left'][a:b], axis=1)
                vote = (vy[a:b] > 100) & np.isfinite(dr) & np.isfinite(dl)
                if vote.sum():
                    f = float(np.mean(dl[vote] < dr[vote]))
                    if 1/3 < f < 2/3: who, rule = None, 'ambiguous'
                    else: who, rule = ('left' if f > .5 else 'right'), 'markers'
                else:
                    core = vy[a:b] > 50; ov = {l: int((stance[l][a:b] & core).sum()) if stance[l] is not None else 0 for l in ('right', 'left')}
                    if ov['left'] != ov['right']: who, rule = ('left' if ov['left'] > ov['right'] else 'right'), 'events'
                    else: who, rule = None, 'unassigned'
                if who: owner[who][a:b, i] = True
                cont.append(dict(plate=p['name'], a=a, b=b, who=who, rule=rule))
    lg('owners')
    res['contacts_mine'] = {'n': len(cont), 'by_rule': {r_: sum(c['rule'] == r_ for c in cont) for r_ in ('markers', 'events', 'ambiguous', 'unassigned')},
                            'by_owner': {w: sum(c['who'] == w for c in cont) for w in ('right', 'left', None)}}
    # compare with stored
    for leg in ('right', 'left'):
        S = leg[0].upper()
        vy_all = np.stack([np.nan_to_num(p['vy']) for p in plates], 1); vx_all = np.stack([np.nan_to_num(p['vx']) for p in plates], 1); vz_all = np.stack([np.nan_to_num(p['vz']) for p in plates], 1)
        own = owner[leg]; vert = np.where(own, vy_all, 0).sum(1) / BW
        allnan = np.stack([np.isnan(p['vy']) for p in plates], 1).all(1); vert[allnan] = np.nan
        sv = stored[f'grf_vertical_{leg}_BW'].values
        both = np.isfinite(sv) & np.isfinite(vert)
        rr = {'vertical_max_diff_BW': float(np.abs(sv[both] - vert[both]).max()), 'finite_mismatch': int((np.isfinite(sv) != np.isfinite(vert)).sum()),
              'loaded_samples_mine': int((vert > 1/BW).sum()), 'loaded_samples_stored': int(stored[f'plate_loaded_{leg}'].sum())}
        loaded = np.nan_to_num(vert) * BW > 1.0
        # Z sign by loaded run, own implementation
        zs = np.full(n, np.nan); k = 0; gated = 0; runs_ = 0
        while k < n:
            if loaded[k]:
                a = k
                while k < n and loaded[k]: k += 1
                h_ = fwdp[a:k]; h_ = h_[np.isfinite(h_).all(1)]
                if len(h_):
                    runs_ += 1; m = h_.mean(0); m /= np.linalg.norm(m)
                    if abs(m[2]) >= math.cos(math.radians(45)): zs[a:k] = np.sign(m[2])
                    else: gated += 1
            else: k += 1
        # forward direction on lab Z with sign zs; person's right = fwd x up; lateral outward = +right (right leg), -right (left leg)
        fz = np.where(own, vz_all, 0).sum(1); fx = np.where(own, vx_all, 0).sum(1)
        fvec = np.stack([fx, np.zeros(n), fz], 1)
        fw = np.stack([np.zeros(n), np.zeros(n), zs], 1); rgt = np.cross(fw, UP)
        ant = np.sum(fvec * fw, 1) / BW
        lat = np.sum(fvec * rgt, 1) / BW * (1 if leg == 'right' else -1)
        for nm, mine in (('anterior', ant), ('lateral', lat)):
            sv = stored[f'grf_{nm}_{leg}_BW'].values; m_ = loaded & np.isfinite(sv) & np.isfinite(mine)
            rr[nm] = {'compared_loaded': int(m_.sum()), 'max_abs_diff_BW': float(np.abs(sv[m_] - mine[m_]).max()) if m_.any() else None,
                      'stored_finite_when_loaded_mine_nan': int((loaded & np.isfinite(sv) & ~np.isfinite(mine)).sum()),
                      'mine_finite_stored_nan_loaded': int((loaded & ~np.isfinite(sv) & np.isfinite(mine)).sum())}
        rr['z_gate'] = {'runs': runs_, 'failed': gated}
        # treadmill: ESML-style signs comparison
        if mode == 'treadmill':
            m_ = loaded & np.isfinite(zs)
            rr['esml_style_anterior_minus_sumvz_corr'] = float(np.corrcoef(stored[f'grf_anterior_{leg}_BW'].values[m_], (-fz / BW)[m_])[0, 1]) if m_.sum() > 10 else None
            rr['esml_style_lateral_sumvx_corr'] = float(np.corrcoef(stored[f'grf_lateral_{leg}_BW'].values[m_], (fx / BW)[m_])[0, 1]) if m_.sum() > 10 else None
        # CoP
        if leg_out[leg].get('fwd') is not None:
            wv = np.where(own & (vy_all > 0) & np.isfinite(np.stack([p['cop'] for p in plates], 1)).all(2), vy_all, 0)
            ws = wv.sum(1); cops = np.nan_to_num(np.stack([p['cop'] for p in plates], 1))
            with np.errstate(invalid='ignore', divide='ignore'):
                pt = np.where(ws[:, None] > 0, np.einsum('np,npk->nk', wv, cops) / ws[:, None], np.nan)
            Lg = leg_out[leg]; held = Lg['held']; fa = Lg['ang']['foot']
            fa_ = np.where(np.isfinite(Lg['foot']), Lg['foot'], np.nan)
            c, s_ = np.cos(Lg['foot'])[:, None], np.sin(Lg['foot'])[:, None]
            ef = c * Lg['fwd'] + s_ * UP; eu = -s_ * Lg['fwd'] + c * UP; er = np.cross(ef, eu)
            q = pt - Lg['A']
            a_ = np.sum(q * ef, 1) - 0.1; v_ = np.sum(q * eu, 1); l_ = np.sum(q * er, 1) * (1 if leg == 'right' else -1)
            bad = ~(vert >= 0.2) | (np.abs(a_) > .5) | (np.abs(l_) > .1) | ~np.isfinite(a_ + v_ + l_) | held
            for nm, mine in (('anterior', a_), ('vertical', v_), ('lateral', l_)):
                mine = np.where(bad, np.nan, mine); sv = stored[f'cop_{nm}_{leg}_m'].values; m_ = np.isfinite(sv) & np.isfinite(mine)
                rr[f'cop_{nm}'] = {'both_finite': int(m_.sum()), 'finite_mismatch': int((np.isfinite(sv) != np.isfinite(mine)).sum()),
                                   'max_abs_diff_m': float(np.abs(sv[m_] - mine[m_]).max()) if m_.any() else None,
                                   'p50_m': float(np.median(mine[m_])) if m_.any() else None}
            # footnote: raw (lab) CoP at plate position consistency: CoP equals plate-reported position by construction (checked by weighted mean)
        # stance agreement of ownership with events
        if stance[leg] is not None:
            ol = (np.nan_to_num(vert) * BW > 50)
            rr['owned_loaded_samples'] = int(ol.sum()); rr['owned_loaded_inside_event_stance_pct'] = float(100 * (ol & stance[leg]).sum() / max(1, ol.sum()))
        res['legs'][leg]['forces'] = rr
    # sum check: both feet vertical sum vs total plate vertical
    tot = np.nansum(np.stack([np.nan_to_num(p['vy']) for p in plates], 1), 1) / BW
    sumboth = np.nan_to_num(stored.grf_vertical_right_BW.values) + np.nan_to_num(stored.grf_vertical_left_BW.values)
    res['sum_of_two_feet_over_all_plates_pct'] = float(100 * sumboth.sum() / max(1e-9, tot.sum()))
    res['n_plate_names'] = len(plates)
# moments
rd_ch('id'); idt = tab['id']
if idt is not None:
    it = np.asarray(idt['Header']); md = 0
    for leg in ('right', 'left'):
        s = leg[0]
        for nm, src_, sg in (('hip_flexion', f'hip_flexion_{s}_moment', 1.), ('knee_flexion', f'knee_angle_{s}_moment', -1.), ('ankle_dorsiflexion', f'ankle_angle_{s}_moment', 1.)):
            mine = np.full(n, np.nan); ins = (t >= it[0]) & (t <= it[-1]); mine[ins] = np.interp(t[ins], it, idt[src_])
            mine = sg * mine / W; sv = stored[f'{nm}_moment_{leg}_Nm_kg'].values; b = np.isfinite(sv) & np.isfinite(mine)
            md = max(md, float(np.abs(sv[b] - mine[b]).max()) if b.any() else 0)
    res['moment_max_diff_Nm_kg'] = md
res['peak_rss_mib'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
print(json.dumps(res, default=lambda o: o.item() if hasattr(o, 'item') else str(o)))
