# GenBox v2.6.0-rc.2

> Experimental client candidate for local evaluation. This is not a stable
> release.

## Candidate Update

- Push keys are shown once by default and are not saved locally.
- A user may explicitly select local saving and confirm before a newly issued
  Push key is encrypted into the local credential vault.
- A locked vault cannot reveal a saved Push key. Rotation requires fresh save
  consent, and deleting a local copy does not change the remote Push source.

## Important Limits

- Source-file cleanup remains disabled by default and is not available in this
  candidate.
- No stable tag or GitHub Release is created for this candidate.
- Remote deployment and production-instance evidence are outside this
  candidate.
