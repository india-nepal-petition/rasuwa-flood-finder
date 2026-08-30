#!/usr/bin/env python3
"""
Rasuwa Flood finder - scheduled scraper.
(1) NDRRMA rescued-persons API  (2) Nepal Police UDB list + detail pages.
Translates to English, fixes dates, tags flood, pulls identifying details
(height/clothes/marks/etc.), de-dupes, writes data/*.json.

Detail pages are fetched ONLY for flood records and ONLY once each (cached from the
previous run's data), so ongoing load on the police server stays small.
"""
import json, os, time, datetime, traceback
import urllib.request
import process as P

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)
UA = "Mozilla/5.0 (compatible; RasuwaFloodFinder/1.0; humanitarian family-tracing aid)"
MAX_ENRICH_PER_RUN = 600

def log(*a): print("[scraper]", *a, flush=True)

def _flatten(rec):
    out = {}
    for k, v in rec.items():
        if v is None: out[k] = ""
        elif isinstance(v, dict): out[k] = v.get("name") or v.get("title") or v.get("name_en") or v.get("en") or v.get("label") or v.get("value") or ""
        elif isinstance(v, list): out[k] = "; ".join(str(x.get("name") if isinstance(x, dict) else x) for x in v)
        else: out[k] = v
    return out

def fetch_rescued():
    base = "https://ndrrma.gov.np/api/v1/rescues/rescued-persons/"
    limit, offset, out = 200, 0, []
    while True:
        url = f"{base}?limit={limit}&offset={offset}"
        for attempt in range(5):
            try:
                req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
                with urllib.request.urlopen(req, timeout=30) as r:
                    j = json.loads(r.read().decode("utf-8"))
                break
            except Exception as e:
                log(f"rescued offset {offset} retry {attempt+1}: {e}"); time.sleep(2*(attempt+1))
        else:
            log("rescued: giving up at offset", offset); break
        batch = j.get("results", j) if isinstance(j, dict) else j
        if not batch: break
        out.extend(_flatten(x) for x in batch)
        offset += limit
        cnt = j.get("count") if isinstance(j, dict) else None
        log(f"rescued: {len(out)}" + (f"/{cnt}" if cnt else ""))
        if cnt is not None and offset >= cnt: break
        if len(batch) < limit: break
        time.sleep(0.8)
    return P.dedupe([P.clean_rescued(r) for r in out], key="id")

UDB_LIST_JS = r"""
async () => {
  const sleep = ms => new Promise(r=>setTimeout(r,ms));
  const LAB=['Name:-','Estimated Age:-','Age:-','Gender:-','Found Place:-','Found Date/Time:-','हाल शव राखेको स्थान:-'];
  const field=(t,l)=>{const i=t.indexOf(l);if(i<0)return'';const s=i+l.length;let nx=t.length;for(const x of LAB){if(x===l)continue;const j=t.indexOf(x,s);if(j>=0&&j<nx)nx=j;}return t.slice(s,nx).replace(/\s+/g,' ').replace(/^[\s,\/]+|[\s,\/]+$/g,'').trim();};
  const parse=doc=>{const out=[];doc.querySelectorAll('tr').forEach(tr=>{if(!tr.querySelector('img'))return;const th=tr.querySelector('th');const sn=th?th.textContent.trim():'';const im=tr.querySelector('img');const photo=im?(im.getAttribute('src')||''):'';let id=(photo.match(/\/(?:photo|dead-bodies)\/(\d+)/)||[])[1]||'';const a=tr.querySelector('a[href*="/dead-bodies/"]');let detail=a?a.href:(id?location.origin+'/dead-bodies/'+id:'');if(!id&&detail){const m=detail.match(/\/dead-bodies\/(\d+)/);if(m)id=m[1];}const flood=tr.textContent.indexOf('रसुवा विपद्को शव')>=0;let text='';tr.querySelectorAll('td').forEach(td=>{const tc=td.textContent;if(tc.indexOf('Found Date/Time:-')>=0||tc.indexOf('Name:-')>=0)text=tc;});if(!text)text=tr.textContent;out.push({sn,id,flood,gender:field(text,'Gender:-'),age:field(text,'Estimated Age:-')||field(text,'Age:-'),found_place:field(text,'Found Place:-'),found_date_raw:field(text,'Found Date/Time:-'),current_location:field(text,'हाल शव राखेको स्थान:-').replace(/\s*View Details\s*$/i,'').trim(),photo,detail,raw_text:tr.textContent});});return out;};
  let COUNT=2100;const cl=document.querySelector('a[href*="count="]');if(cl){const m=cl.href.match(/count=(\d+)/);if(m)COUNT=m[1];}
  const all=[];let empty=0;
  for(let n=1;n<=150;n++){let recs=null;for(let t=0;t<4&&recs===null;t++){try{const res=await fetch(`${location.origin}/dead-bodies-lists?&count=${COUNT}&page=${n}`,{credentials:'same-origin'});if(!res.ok)throw 0;recs=parse(new DOMParser().parseFromString(await res.text(),'text/html'));}catch(e){await sleep(1500*(t+1));}}if(recs===null){continue;}if(recs.length===0){if(++empty>=2)break;continue;}empty=0;all.push(...recs);await sleep(700);}
  return all;
}
"""
FETCH_ONE_JS = "async (u) => { try { const r = await fetch(u, {credentials:'same-origin'}); if(!r.ok) return ''; return await r.text(); } catch(e){ return ''; } }"

def fetch_deceased(cache):
    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:
        log("Playwright not available:", e); return None
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(args=["--no-sandbox"])
            page = browser.new_page(user_agent=UA)
            page.goto("https://udb.nepalpolice.gov.np/dead-bodies", timeout=60000, wait_until="networkidle")
            page.wait_for_timeout(2500)
            rows = page.evaluate(UDB_LIST_JS)
            if not rows:
                log("UDB returned 0 rows (possible block)"); browser.close(); return None
            deceased = P.dedupe([P.clean_deceased(r) for r in rows], key="id")
            need = []
            for r in deceased:
                prev = cache.get(r.get("id"))
                if prev and prev.get("enriched"):
                    for k in ("height","weight","build","complexion","eye_colour","hair_colour",
                              "clothes","shoes","personal","marks","special","ethnicity","reg_no",
                              "found_full","enriched"):
                        if prev.get(k): r[k] = prev[k]
                    if prev.get("current_location"): r["current_location"] = prev["current_location"]
                elif r.get("flood") and r.get("detail_url"):
                    need.append(r)
            log(f"deceased: {len(deceased)} list rows; {len(need)} flood records need details")
            for i, r in enumerate(need[:MAX_ENRICH_PER_RUN]):
                html = page.evaluate(FETCH_ONE_JS, r["detail_url"])
                if html:
                    r.update(P.clean_detail(html))
                if (i+1) % 25 == 0: log(f"  details {i+1}/{min(len(need),MAX_ENRICH_PER_RUN)}")
                time.sleep(0.5)
            browser.close()
            return deceased
    except Exception as e:
        log("UDB browser fetch failed:", e); traceback.print_exc(); return None

def load_existing(name):
    try: return json.load(open(os.path.join(DATA_DIR, name), encoding="utf-8"))
    except Exception: return []

def main():
    rescued = deceased = None
    try: rescued = fetch_rescued()
    except Exception: log("rescued error"); traceback.print_exc()
    cache = {r.get("id"): r for r in load_existing("deceased.json")}
    try: deceased = fetch_deceased(cache)
    except Exception: log("deceased error"); traceback.print_exc()
    if not rescued: rescued = load_existing("rescued.json"); log("rescued: kept previous", len(rescued))
    if not deceased: deceased = list(cache.values()); log("deceased: kept previous", len(deceased))
    json.dump(rescued, open(os.path.join(DATA_DIR,"rescued.json"),"w",encoding="utf-8"), ensure_ascii=False)
    json.dump(deceased, open(os.path.join(DATA_DIR,"deceased.json"),"w",encoding="utf-8"), ensure_ascii=False)
    meta = {
        "last_updated": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "rescued_count": len(rescued), "deceased_count": len(deceased),
        "deceased_flood": sum(1 for d in deceased if d.get("flood")),
        "deceased_enriched": sum(1 for d in deceased if d.get("enriched")),
        "rescued_foreign": sum(1 for r in rescued if str(r.get("nationality","")).lower()=="foreign"),
        "sources": ["Nepal Police UDB", "NDRRMA Rescue"],
    }
    json.dump(meta, open(os.path.join(DATA_DIR,"meta.json"),"w",encoding="utf-8"), ensure_ascii=False, indent=2)
    log("done:", meta)

if __name__ == "__main__":
    main()
