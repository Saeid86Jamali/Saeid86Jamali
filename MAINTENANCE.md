# Portfolio maintenance

This repository maintains a reviewed public research profile. The Python monitor
and its safeguard tests have been run locally. Consult the repository Actions
page for hosted validation and review results; deployment alone does not prove
that a future scheduled run will succeed.

## Public record

`portfolio.json` contains reviewed public metadata only. `README.template.md`
contains editorial text; `scripts/portfolio.py render` generates `README.md`.
The three published records were checked against publisher and DOI metadata.
Two linked arXiv records are preprint versions of those publications, not two
additional papers. The group-actions preprint has a different title from the
published article. Author order is preserved.

Status vocabulary: `in_progress`, `submitted`, `preprint`, `accepted`, `published`.
These states require evidence, not an automatic promotion based on a filename,
cover letter, PDF review header, assistant assessment or elapsed time. A preprint
and a journal submission can coexist; public presentation must describe both
accurately when disclosure is authorized.

## What the monitor does

```bash
python3 -m unittest discover -s tests -v
python3 scripts/portfolio.py render --check
python3 scripts/portfolio.py monitor
```

The monitor collects the public GitHub profile/repository inventory, an arXiv
author search, and Crossref records for the three known DOIs. It compares each
successfully fetched source with `monitoring-baseline.json` and produces
`review/observed.json`, `changes.json` and `summary.md`. Source failure produces
a partial result and a failing exit code; it is never interpreted as deletion.
New arXiv name matches remain candidates requiring identity review.
The profile repository’s own push timestamp is retained in evidence but ignored
in comparisons, so committing a reviewed baseline does not trigger itself.
Changes to its metadata and other repositories’ push times are still reported.

It cannot detect a private submission, acceptance email, private dataset, new
ChatGPT conversation or unreleased experiment. It does not change GitHub settings,
write scientific claims, create a publication, or copy files into a public repository.
Crossref and arXiv can lag publisher records; the absence of a journal reference
in arXiv does not undo verified publication status.

## Review and synchronization

1. Verify each observed change against the actual paper, publisher page or
   explicitly supplied evidence. Check author identity and author order.
2. Obtain approval before releasing private material or altering scientific
   claims. Confirm anonymous-review and coauthor restrictions. Keep these
   deliberations outside public issues and commit messages.
3. Update the reviewed public registry and run `render`.
4. Review the diff and run the tests and `render --check`.
5. Commit the registry and generated README together. Preserve an update note
   containing the source, previous/new status, date and commit identifier.
6. Advance the monitoring baseline only after reviewing a complete observation.
   Never accept a partial snapshot as a complete baseline.

The workflow has read-only repository permission and cannot push or auto-merge.
This keeps publishing changes to scientific claims in the review path. After a
reviewed commit, the profile README is synchronized deterministically with the
registry; CI detects drift.

## Deployment and recovery checklist

- Authenticate to the confirmed `Saeid86Jamali` account through an authorized route.
- Inspect all private repositories and any existing profile repository first.
- Install these files in the special profile repository `Saeid86Jamali/Saeid86Jamali`
  only after verifying it does not already contain work. Preserve existing history.
- Keep the entire parent preparation package private; copy only this public-ready
  profile directory. Never upload private inventory, author-only notes or archives.
- Use the existing default branch and run the workflow manually once. Verify both
  checks, the review summary and the downloaded artifact before calling it active.
- Confirm the first scheduled run. The Actions cron is Monday 16:23 UTC
  (08:23 Pacific in winter, 09:23 in summer); it is not a fixed local time.

GitHub schedules run from the default branch, can be delayed, and can be disabled
after 60 days without public-repository activity. Check run health during the
separate weekly review; do not generate meaningless commits to keep it alive.
See [GitHub's scheduling documentation](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows)
and the [arXiv API manual](https://info.arxiv.org/help/api/user-manual.html).

## Future update intake

Provide the following privately in the GitHub-maintenance conversation:

```text
GitHub update
Project/title:
Milestone and date:
Exact status (in progress / submitted / preprint / accepted / published):
Authors in order:
Public DOI/arXiv/repository link or private evidence:
Exact code/data/manuscript files authorized for public release:
Anonymous-review, coauthor, license or data restrictions:
Result or claim changed, with evidence:
```

An upload alone authorizes inspection, not public release. No license is inferred
for unpublished code or data. A journal publisher's PDF is linked instead of
redistributed unless rights are confirmed. Record AI assistance accurately for
each project; do not replace author contributions with generic authorship claims.
