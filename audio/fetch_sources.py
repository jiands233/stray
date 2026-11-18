import urllib.request,re,json,concurrent.futures
from pathlib import Path
P=Path('/workspace/stray/audio')
urls={'siren':'https://freesound.org/people/Breviceps/sounds/581381/','glass':'https://freesound.org/people/C_Rogers/sounds/203371/','engine':'https://freesound.org/people/PritzProductions/sounds/241083/','helicopter':'https://freesound.org/people/EminYILDIRIM/sounds/536927/','explosion':'https://freesound.org/people/Rudmer_Rotteveel/sounds/336004/'}
def get(pair):
 name,url=pair
 try:
  d=urllib.request.urlopen(url,timeout=25).read().decode();(P/(name+'_source.html')).write_text(d)
  lic=re.findall(r'href="(https?://creativecommons.org/[^\"]+)',d)
  preview=re.search(r'https://cdn.freesound.org/previews/[^\s\"\'<>]+-lq.mp3',d).group().replace('-lq.mp3','-hq.mp3')
  urllib.request.urlretrieve(preview,str(P/(name+'.mp3')))
  print(json.dumps({'name':name,'page':url,'license':list(set(lic)),'download':preview}),flush=True)
  return {'name':name,'page':url,'license':list(set(lic)),'download':preview,'file':name+'.mp3'}
 except Exception as e:print(name,str(e),flush=True);return {'name':name,'page':url,'error':str(e)}
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:r=list(ex.map(get,urls.items()))
(P/'sources.json').write_text(json.dumps(r,indent=2))
