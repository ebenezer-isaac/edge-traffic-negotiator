import json,glob,math,statistics as st
SEEDS=sorted(set(range(1,31))-{3,7,11,29} | {31,32,33,34})
ft={}
for fn in ['experiment_fixedtime_seed30.json','experiment_fixedtime_calibrated.json','experiment_fixedtime_guards.json']:
    for c in json.load(open(fn))['cells']:
        ft.setdefault((c['topology'],c['seed']), c['fixedtime_delay_s'])
mp={}
for f in glob.glob('frontier_raw/BASELINE__*.json'):
    d=json.load(open(f)); mp[(d['topology'],d['seed'])]=d['mean_network_delay_s']
def betacf(a,b,x):
    MAX=300; EPS=3e-16; FP=1e-300
    qab=a+b; qap=a+1; qam=a-1
    c=1.0; d=1.0-qab*x/qap
    if abs(d)<FP: d=FP
    d=1/d; h=d
    for m in range(1,MAX+1):
        m2=2*m
        aa=m*(b-m)*x/((qam+m2)*(a+m2))
        d=1+aa*d
        if abs(d)<FP: d=FP
        c=1+aa/c
        if abs(c)<FP: c=FP
        d=1/d; h*=d*c
        aa=-(a+m)*(qab+m)*x/((a+m2)*(qap+m2))
        d=1+aa*d
        if abs(d)<FP: d=FP
        c=1+aa/c
        if abs(c)<FP: c=FP
        d=1/d; de=d*c; h*=de
        if abs(de-1)<EPS: break
    return h
def betai(a,b,x):
    if x<=0: return 0.0
    if x>=1: return 1.0
    bt=math.exp(math.lgamma(a+b)-math.lgamma(a)-math.lgamma(b)+a*math.log(x)+b*math.log(1-x))
    if x < (a+1)/(a+b+2): return bt*betacf(a,b,x)/a
    return 1-bt*betacf(b,a,1-x)/b
def tp(t,df): return betai(df/2,0.5,df/(df+t*t))
def tcrit(df):
    lo,hi=0.,200.
    for _ in range(300):
        mid=(lo+hi)/2
        if tp(mid,df)>0.05: lo=mid
        else: hi=mid
    return (lo+hi)/2
def onesample(v):
    n=len(v); m=st.mean(v); s=st.stdev(v); se=s/math.sqrt(n); t=m/se
    tc=tcrit(n-1)
    return n,m,(m-tc*se,m+tc*se),tp(t,n-1)
def paired(a,b):
    return onesample([x-y for x,y in zip(a,b)])
