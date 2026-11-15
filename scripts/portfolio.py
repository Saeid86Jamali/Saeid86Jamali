#!/usr/bin/env python3
"""Generate a reviewed profile and collect public metadata without publishing it."""
import argparse
import datetime as dt
import json
import pathlib
import re
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parents[1]
ATOM = {'a':'http://www.w3.org/2005/Atom','ar':'http://arxiv.org/schemas/atom',
        'os':'http://a9.com/-/spec/opensearch/1.1/'}

def load_registry(path=ROOT/'portfolio.json'):
    data=json.loads(path.read_text())
    if data.get('schema_version') != 1:
        raise ValueError('Unsupported registry version')
    seen=set()
    for p in data['publications']:
        if p['id'] in seen:
            raise ValueError('Duplicate publication identifier')
        seen.add(p['id'])
        if p.get('public_release_approved') is not True:
            raise ValueError('Private or unapproved entries must remain outside this public registry')
        if p['status'] not in {'published','accepted','preprint','submitted','in_progress'}:
            raise ValueError('Unknown publication status')
        if 'Saeid Jamali' not in p['authors']:
            raise ValueError('Author identity not verified')
        if p['status']=='published' and not p.get('doi'):
            raise ValueError('Published entry needs a verified DOI')
        if not p.get('source','').startswith('https://'):
            raise ValueError('Entry needs an evidence URL')
        if p.get('doi') and not re.fullmatch(r'10\.\d{4,9}/[A-Za-z0-9._;()/:-]+',p['doi']):
            raise ValueError('Invalid DOI')
        if p.get('arxiv') and not re.fullmatch(r'\d{4}\.\d{4,5}',p['arxiv']):
            raise ValueError('Invalid arXiv ID')
    return data

def escape_md(value):
    return re.sub(r'([\\`*_{}\[\]<>|])',r'\\\1',str(value).replace('\n',' '))

def render(data,template):
    rows=[]
    for p in data['publications']:
        names='; '.join(escape_md(a) for a in p['authors'])
        title=escape_md(p['title'])
        if p.get('doi'):
            title=f"[{title}](https://doi.org/{p['doi']})"
        venue=escape_md(p.get('journal',''))
        if p['status']=='published':
            detail=f"*{venue}* **{p['volume']}**({p['issue']}), {p['pages']} ({p['year']})."
        else:
            detail=f"{p['status'].replace('_',' ').capitalize()} ({p['year']})."
        preprint=f" [arXiv](https://arxiv.org/abs/{p['arxiv']})." if p.get('arxiv') else ''
        rows.append(f"{len(rows)+1}. **{title}.** {names}. {detail}{preprint}")
    projects=[]
    for p in data.get('projects',[]):
        if p.get('public_release_approved') is not True:
            raise ValueError('Unapproved project in public registry')
        url=p.get('repository','')
        if not re.fullmatch(r'https://github\.com/Saeid86Jamali/[A-Za-z0-9_.-]+',url):
            raise ValueError('Project needs a verified owned repository URL')
        projects.append(f"- [{escape_md(p['name'])}]({url}): {escape_md(p['description'])}")
    if template.count('<!-- PUBLICATIONS -->') != 1 or template.count('<!-- PROJECTS -->') != 1:
        raise ValueError('Template markers missing or duplicated')
    return template.replace('<!-- PUBLICATIONS -->','\n\n'.join(rows)).replace('<!-- PROJECTS -->','\n'.join(projects))

def fetch(url):
    req=urllib.request.Request(url,headers={'User-Agent':'SaeidJamali-ResearchPortfolio/1.0 (public metadata audit)','Accept':'application/json, application/atom+xml'})
    with urllib.request.urlopen(req,timeout=25) as response:
        return response.read()

def parse_arxiv(raw):
    root=ET.fromstring(raw)
    if root.tag != '{http://www.w3.org/2005/Atom}feed':
        raise ValueError('Not an Atom feed')
    total_text=root.findtext('os:totalResults',default='',namespaces=ATOM)
    if not total_text.isdigit() or int(total_text)>100:
        raise ValueError('Incomplete or oversized arXiv response: manual pagination required')
    records={}
    for e in root.findall('a:entry',ATOM):
        url=e.findtext('a:id',default='',namespaces=ATOM)
        match=re.fullmatch(r'https?://arxiv\.org/abs/(\d{4}\.\d{4,5})(v\d+)?',url)
        if not match:
            raise ValueError('Unrecognized arXiv entry, possibly API error')
        authors=[n.text for n in e.findall('a:author/a:name',ATOM)]
        records[match.group(1)]={'id':match.group(1),'version':match.group(2),
          'title':' '.join(e.findtext('a:title',default='',namespaces=ATOM).split()),
          'authors':authors,'updated':e.findtext('a:updated',namespaces=ATOM),
          'doi':e.findtext('ar:doi',namespaces=ATOM),
          'journal_ref':e.findtext('ar:journal_ref',namespaces=ATOM),
          'identity_status':'candidate_requires_review'}
    if len(records)!=int(total_text):
        raise ValueError('arXiv result count mismatch')
    return records

def crossref_record(raw,doi):
    payload=json.loads(raw)
    if payload.get('status')!='ok' or not isinstance(payload.get('message'),dict):
        raise ValueError('Invalid Crossref response')
    m=payload['message']
    if m.get('DOI','').lower()!=doi.lower():
        raise ValueError('Crossref DOI mismatch')
    return {k:m.get(k) for k in ['DOI','title','author','container-title','volume','issue','page','published','relation','update-to','updated-by']}

def collect(data,fetcher=fetch):
    result={'schema_version':1,'checked_at':dt.datetime.now(dt.timezone.utc).isoformat(),
            'sources':{},'errors':{}}
    def capture(name,fn):
        try:result['sources'][name]=fn()
        except Exception as exc:result['errors'][name]=f'{type(exc).__name__}: {exc}'
    def gh_profile():
        u=json.loads(fetcher('https://api.github.com/users/Saeid86Jamali'))
        if u.get('login')!='Saeid86Jamali':raise ValueError('GitHub identity mismatch')
        return {k:u.get(k) for k in ['login','name','bio','company','blog','public_repos']}
    def gh_repos():
        all_repos=[]
        for page in range(1,11):
            rows=json.loads(fetcher(f'https://api.github.com/users/Saeid86Jamali/repos?per_page=100&type=owner&sort=full_name&page={page}'))
            if not isinstance(rows,list):raise ValueError('Invalid GitHub repository response')
            for r in rows:
                if r.get('owner',{}).get('login')!='Saeid86Jamali' or r.get('private') is not False:
                    raise ValueError('Unexpected owner or nonpublic repository')
                all_repos.append({k:r.get(k) for k in ['name','description','topics','pushed_at','archived','default_branch','html_url']})
            if len(rows)<100:return sorted(all_repos,key=lambda r:r['name'])
        raise ValueError('Repository inventory exceeds safety limit')
    def arxiv():
        query=urllib.parse.urlencode({'search_query':'au:"Saeid Jamali"','start':0,'max_results':100,'sortBy':'lastUpdatedDate','sortOrder':'descending'})
        records=parse_arxiv(fetcher('https://export.arxiv.org/api/query?'+query))
        expected={p['arxiv'] for p in data['publications'] if p.get('arxiv')}
        if not expected.issubset(records):raise ValueError('Known arXiv records missing; do not infer withdrawal')
        for key in expected:
            if 'Saeid Jamali' not in records[key]['authors']:raise ValueError('Known arXiv author identity mismatch')
            records[key]['identity_status']='known_public_record'
        return records
    capture('github_profile',gh_profile)
    capture('github_repositories',gh_repos)
    capture('arxiv_author_search',arxiv)
    for p in data['publications']:
        if p.get('doi'):
            doi=p['doi']
            capture('crossref:'+doi,lambda doi=doi:crossref_record(fetcher('https://api.crossref.org/works/'+urllib.parse.quote(doi,safe='')),doi))
    result['status']='complete' if not result['errors'] else 'partial'
    return result

def compare(previous,current):
    changes=[]
    for source,new in current.get('sources',{}).items():
        old=previous.get('sources',{}).get(source)
        if old!=new:changes.append({'source':source,'previous':old,'observed':new,'action':'review_required'})
    return changes

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='cmd',required=True)
    gen=sub.add_parser('render');gen.add_argument('--check',action='store_true')
    monitor=sub.add_parser('monitor');monitor.add_argument('--output',type=pathlib.Path,default=ROOT/'review')
    args=parser.parse_args();data=load_registry()
    if args.cmd=='render':
        text=render(data,(ROOT/'README.template.md').read_text())
        if args.check:
            if not (ROOT/'README.md').exists() or (ROOT/'README.md').read_text()!=text:
                raise SystemExit('README differs from reviewed registry; run render and review the diff')
        else:(ROOT/'README.md').write_text(text)
        return
    current=collect(data)
    baseline=ROOT/'monitoring-baseline.json'
    previous=json.loads(baseline.read_text()) if baseline.exists() else {'sources':{}}
    changes=compare(previous,current)
    args.output.mkdir(parents=True,exist_ok=True)
    (args.output/'observed.json').write_text(json.dumps(current,indent=2)+'\n')
    (args.output/'changes.json').write_text(json.dumps(changes,indent=2)+'\n')
    summary=['# Public portfolio review',f"Checked: {current['checked_at']}",f"Status: {current['status']}",f'Changed source sections: {len(changes)}',
      'This check does not edit GitHub, change publication status, or approve a release.']
    summary += ['- Review '+c['source'] for c in changes]
    summary += ['- Source failed: '+k+' — '+v for k,v in current['errors'].items()]
    summary += ['Compare changes.json with primary sources. Name matches are candidates, not proof of identity.',
                'After review, update portfolio.json and regenerate README.md in the same commit.',
                'Replace monitoring-baseline.json only after reviewing all complete observations.']
    (args.output/'summary.md').write_text('\n\n'.join(summary)+'\n')
    print(json.dumps({'status':current['status'],'changed_sections':len(changes),'errors':current['errors']},indent=2))
    if current['errors']:raise SystemExit(2)

if __name__=='__main__':main()
