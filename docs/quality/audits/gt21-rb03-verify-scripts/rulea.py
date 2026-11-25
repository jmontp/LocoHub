import re,json,glob,sys,collections
M='/mnt/s/workspace/locomotion-data-standardization/contributor_tools/conversion_scripts/Gtech_2021/CAMARGO_ET_AL_J_BIOMECH_DATASET/scripts (1)/STRIDES.m'
txt=open(M,encoding='utf-8',errors='replace').read().replace('\r','')
lines=txt.split('\n')
# locate the classification loop and the three mode blocks
def block(start_pat,end_pat):
    s=[i for i,l in enumerate(lines) if re.search(start_pat,l)][0]
    e=[i for i,l in enumerate(lines) if i>s and re.search(end_pat,l)][0]
    return lines[s+1:e]
lg=block(r"if strcmp\(ambulationMode,'levelground'\)",r"elseif strcmp\(ambulationMode,'ramp'\)")
rp=block(r"elseif strcmp\(ambulationMode,'ramp'\)",r"elseif strcmp\(ambulationMode,'stair'\)")
st=block(r"elseif strcmp\(ambulationMode,'stair'\)",r"\[u_labels")
def translate(cond):
    c=cond
    c=re.sub(r'all\(strcmp\(labels\.Label\{1\},\'([\w-]+)\'\)\)',r"(L[0]=='\1')",c)
    c=re.sub(r"all\(strcmp\(labels\.Label,'([\w-]+)'\)\)",r"all(x=='\1' for x in L)",c)
    c=re.sub(r"any\(strcmp\(labels\.Label,'([\w-]+)'\)\)",r"any(x=='\1' for x in L)",c)
    c=re.sub(r"any\(contains\(labels\.Label,'([\w-]+)'\)\)",r"any('\1' in x for x in L)",c)
    c=re.sub(r"strcmp\(labels\.Label\{(1|end)\},'([\w-]+)'\)",lambda m:f"(L[{0 if m.group(1)=='1' else -1}]=='{m.group(2)}')",c)
    c=re.sub(r"strcmp\(c\.turn,'(\w+)'\)",r"(TURN=='\1')",c)
    c=re.sub(r"c\.leadingLegStart\{1\}=='(\w)'",r"(LS[0]=='\1')",c)
    c=re.sub(r"c\.leadingLegStop\{1\}=='(\w)'",r"(LP[0]=='\1')",c)
    c=re.sub(r"c\.transLegAscent\((\d)\)=='(\w)'",lambda m:f"(TA[{int(m.group(1))-1}]=='{m.group(2)}')",c)
    c=re.sub(r"c\.transLegDescent\((\d)\)=='(\w)'",lambda m:f"(TD[{int(m.group(1))-1}]=='{m.group(2)}')",c)
    c=c.replace('&&',' and ')
    assert not re.search(r'strcmp|contains|labels|c\.',c),(cond,c)
    return c
def parse(bl):
    # join continuation lines
    stmts=[];buf=''
    for l in bl:
        l=re.sub(r'%.*$','',l).rstrip()
        if not l.strip(): continue
        if l.endswith('...'): buf+=' '+l[:-3]; continue
        buf+=' '+l; stmts.append(buf.strip()); buf=''
    rules=[];cur=None
    for s in stmts:
        m=re.match(r'(?:if|elseif)\s+\(?(.*)$',s)
        if re.match(r'(if|elseif)\b',s):
            cond=m.group(1)
            # strip trailing parenthesis if the original had if ( ... ) wrap
            cur={'cond':cond,'act':None}; rules.append(cur)
        elif re.match(r'else\b',s): cur={'cond':None,'act':'NOTFOUND'}; rules.append(cur)
        else:
            m=re.search(r"alllabels\{j\}='([\w-]+)'",s)
            if m: cur['act']=m.group(1)
            elif s.startswith('continue') and cur['act'] is None: cur['act']='discard'
    out=[]
    for r in rules:
        if r['cond'] is None: out.append((None,r['act'])); continue
        cond=r['cond']
        # handle if (a ... ) paren-wrapped: balance
        while cond.count('(')<cond.count(')') and cond.endswith(')'): cond=cond[:-1]
        if cond.startswith('(') and cond.count('(')>cond.count(')'): pass
        out.append((compile(translate(cond).strip(),'<c>','eval'),r['act']))
    return out
RULES={'levelground':parse(lg),'ramp':parse(rp),'stair':parse(st)}
def classify(mode,L,LS=None,LP=None,TA=None,TD=None,TURN=None):
    for cond,act in RULES[mode]:
        if cond is None or eval(cond,{},dict(L=L,LS=LS,LP=LP,TA=TA,TD=TD,TURN=TURN)): return act
if __name__=='__main__':
    for m,r in RULES.items(): print(m,len(r),[a for _,a in r][:40])
