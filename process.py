"""Shared processing: translate to English, fix dates, tag flood, dedupe.
Used by both the one-off data build and the scheduled scraper."""
import re, datetime
from translit import to_english

FLOOD_START = "2026-08-26"
FLOOD_BADGE = "रसुवा विपद्को शव"
FLOOD_DISTRICTS = ["Rasuwa","Nuwakot","Nawalparasi","Chitwan","Dhading","Sindhupalchok"]

REF_AD = datetime.date(2023,4,14)
CAL = {2080:[31,32,31,32,31,30,30,30,29,29,30,30],2081:[31,32,31,32,31,30,30,30,29,30,29,31],
2082:[31,31,32,31,31,31,30,29,30,29,30,30],2083:[31,31,32,31,31,31,30,29,30,29,30,30],
2084:[31,31,32,31,31,30,30,30,29,30,30,30],2085:[31,32,31,32,30,31,30,30,29,30,30,30],
2086:[30,32,31,32,31,30,30,30,29,30,30,30]}
def _bs2ad(y,m,d):
    if y not in CAL: return ""
    days=sum(sum(CAL[k]) for k in range(2080,y))+sum(CAL[y][:m-1])+(d-1)
    return (REF_AD+datetime.timedelta(days=days)).isoformat()
def _nd(s): return (s or "").translate(str.maketrans("०१२३४५६७८९","0123456789"))
def parse_date(fd):
    """Return (bs, ad). Handles Nepali(BS) or Gregorian(AD) source."""
    m=re.search(r"(\d{4})-(\d{1,2})-(\d{1,2})", _nd(fd or ""))
    if not m: return ("","")
    y,mo,d=int(m.group(1)),int(m.group(2)),int(m.group(3))
    if y>=2070: return (f"{y}-{mo}-{d}", _bs2ad(y,mo,d))
    return ("", f"{y}-{mo:02d}-{d:02d}")
def parse_time(fd):
    m=re.search(r"(\d{1,2})[:;.](\d{2})", _nd(fd or ""))
    return f"{m.group(1)}:{m.group(2)}" if m else ""

def is_flood(raw_text, ad_date, place_en):
    if FLOOD_BADGE in (raw_text or ""): return True
    if ad_date and ad_date >= FLOOD_START: return True
    if any(d in (place_en or "") for d in FLOOD_DISTRICTS) and ad_date and ad_date>="2026-08-01": return True
    return False

def clean_rescued(rec):
    """rec: raw dict from NDRRMA api (id,name,name_ne,age,rescued_location,stationed_location,status,rescued_date,nationality,country,remarks)"""
    name_en=(rec.get("name") or "").strip() or to_english(rec.get("name_ne",""))
    return {
        "id": rec.get("id",""),
        "name": name_en,
        "name_original": rec.get("name_ne") or rec.get("name",""),
        "age": rec.get("age",""),
        "gender": (rec.get("gender","") or "").title(),
        "nationality": (rec.get("nationality","") or "").title(),
        "country": rec.get("country","") or "",
        "status": rec.get("status","") or "",
        "rescued_from": to_english(rec.get("rescued_location","")),
        "stationed_at": to_english(rec.get("stationed_location","")),
        "rescued_date": rec.get("rescued_date","") or "",
        "remarks": to_english(rec.get("remarks","")),
    }

def clean_deceased(rec):
    """rec: raw dict (sn,id,gender,age,found_place,found_date_raw,current_location,photo,detail,raw_text)"""
    place_en=to_english(rec.get("found_place",""))
    bs,ad=parse_date(rec.get("found_date_raw",""))
    if not (bs or ad) and rec.get("found_date_ad"):   # already-parsed source (from CSV)
        ad=rec.get("found_date_ad",""); bs=rec.get("found_date_bs","")
    loc_en=to_english(rec.get("current_location",""))
    return {
        "sn": rec.get("sn",""),
        "id": rec.get("id",""),
        "gender": (rec.get("gender","") or "").title(),
        "age": rec.get("age",""),
        "found_place": place_en,
        "found_place_original": rec.get("found_place",""),
        "found_date_ad": ad,
        "found_date_bs": bs,
        "time": rec.get("time","") or parse_time(rec.get("found_date_raw","")),
        "current_location": loc_en,
        "flood": is_flood(rec.get("raw_text",""), ad, place_en),
        "photo_url": rec.get("photo",""),
        "detail_url": rec.get("detail",""),
    }

def dedupe(rows, key="id"):
    seen=set(); out=[]
    for r in rows:
        k=r.get(key) or id(r)
        if k in seen: continue
        seen.add(k); out.append(r)
    return out

# ---------------- detail-page enrichment ----------------
import re as _re
def _norm_label(s): return _re.sub(r'\s*:\s*$','',_re.sub(r'\s+',' ',s)).strip()
def extract_detail_fields(html):
    pairs=_re.findall(r'<strong[^>]*>([^<]*)</strong>\s*<span[^>]*>([^<]*)</span>', html or '')
    d={}
    for k,v in pairs:
        k=_norm_label(k); v=_re.sub(r'\s+',' ',v).strip()
        if k and k not in d: d[k]=v
    return d
def clean_detail(raw):
    d = extract_detail_fields(raw) if isinstance(raw,str) else (raw or {})
    def g(*labels):
        for L in labels:
            if d.get(L) and d[L] not in ('-','ft','N/A'): return d[L]
        return ''
    out={
      'height':to_english(g('Height')),'weight':to_english(g('Weight')),
      'build':to_english(g('Physical Build')),'complexion':to_english(g('Complexion','Skin Colour')),
      'eye_colour':to_english(g('Eye Colour')),'hair_colour':to_english(g('Hair Colour')),
      'clothes':to_english(g('Clothes Worn')),'shoes':to_english(g('Shoes')),
      'personal':to_english(g('Personal Things')),'marks':to_english(g('Skin marks / old wounds / injuries','Identifying Marks')),
      'special':to_english(g('Special Mark')),'ethnicity':to_english(g('Ethnicity')),
      'reg_no':g('Registration Number'),
    }
    prov,dist=to_english(g('Province')),to_english(g('District'))
    mun=to_english(g('Rural Municipality / Municipality','Municipality'))
    tole,ward=to_english(g('Tole Name')),to_english(g('Ward Number'))
    parts=[p for p in [tole,('Ward '+ward) if ward else '',mun,dist,prov] if p]
    out['found_full']=', '.join(parts)
    cl=g('हाल शव राखेको स्थान')
    if cl: out['current_location']=to_english(cl)
    out['enriched']=True
    return {k:v for k,v in out.items() if v}
