import copy
import importlib.util
import json
import pathlib
import tempfile
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('portfolio',ROOT/'scripts/portfolio.py')
p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)

class SafetyTests(unittest.TestCase):
    def test_unapproved_publication_rejected(self):
        data=json.loads((ROOT/'portfolio.json').read_text());data['publications'][0]['public_release_approved']=False
        with tempfile.TemporaryDirectory() as d:
            path=pathlib.Path(d)/'registry.json';path.write_text(json.dumps(data))
            with self.assertRaises(ValueError):p.load_registry(path)
    def test_submitted_does_not_render_as_published(self):
        d=p.load_registry();d['publications']=d['publications'][:1];d['publications'][0]['status']='submitted'
        out=p.render(d,'<!-- PUBLICATIONS -->\n<!-- PROJECTS -->')
        self.assertIn('Submitted',out);self.assertNotIn('2135',out)
    def test_same_name_new_arxiv_entry_remains_candidate(self):
        xml='''<feed xmlns="http://www.w3.org/2005/Atom" xmlns:os="http://a9.com/-/spec/opensearch/1.1/"><os:totalResults>1</os:totalResults><entry><id>http://arxiv.org/abs/9999.12345v1</id><title>Example</title><author><name>Saeid Jamali</name></author></entry></feed>'''
        self.assertEqual(p.parse_arxiv(xml)['9999.12345']['identity_status'],'candidate_requires_review')
    def test_api_error_is_not_empty_success(self):
        with self.assertRaises(ValueError):p.parse_arxiv(b'<feed xmlns="http://www.w3.org/2005/Atom"><entry><id>http://arxiv.org/api/errors</id></entry></feed>')
    def test_partial_source_failure_is_not_deletion(self):
        self.assertEqual(p.compare({'sources':{'arxiv':[1]}},{'sources':{},'errors':{'arxiv':'offline'}}),[])
    def test_no_change_idempotent(self):
        a={'sources':{'arxiv':{'x':1}},'checked_at':'yesterday'};b=copy.deepcopy(a);b['checked_at']='today'
        self.assertEqual(p.compare(a,b),[])
    def test_profile_baseline_commit_does_not_hide_real_changes(self):
        a={'sources':{'github_repositories':[{'name':'Saeid86Jamali','pushed_at':'old','description':'profile'}, {'name':'research','pushed_at':'old','description':'experiment'}]}}
        b=copy.deepcopy(a);b['sources']['github_repositories'][0]['pushed_at']='new'
        self.assertEqual(p.compare(a,b),[])
        self.assertEqual(b['sources']['github_repositories'][0]['pushed_at'],'new')
        b['sources']['github_repositories'][0]['description']='changed profile'
        self.assertEqual(len(p.compare(a,b)),1)
        b=copy.deepcopy(a);b['sources']['github_repositories'][1]['pushed_at']='new'
        self.assertEqual(len(p.compare(a,b)),1)
    def test_mismatched_doi_rejected(self):
        with self.assertRaises(ValueError):p.crossref_record(json.dumps({'status':'ok','message':{'DOI':'10.0000/wrong'}}),'10.1234/right')
    def test_total_network_failure_is_partial(self):
        def offline(_):raise OSError('offline')
        r=p.collect(p.load_registry(),offline)
        self.assertEqual(r['status'],'partial');self.assertEqual(len(r['errors']),6);self.assertEqual(r['sources'],{})
    def test_wrong_account_rejected(self):
        def wrong(_):return b'{"login":"someone-else"}'
        r=p.collect(p.load_registry(),wrong)
        self.assertIn('github_profile',r['errors']);self.assertNotIn('github_profile',r['sources'])
    def test_unapproved_project_rejected(self):
        d=p.load_registry();d['projects']=[{'name':'private'}]
        with self.assertRaises(ValueError):p.render(d,'<!-- PUBLICATIONS -->\n<!-- PROJECTS -->')

if __name__=='__main__':unittest.main()
