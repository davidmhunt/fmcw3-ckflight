# software/

Installers for the desktop tools the simulation image (`fmcw3-sim`) runs under Wine. Separate
from `datasheets/`, which holds datasheets and models. `manifest.yaml` lists each installer with
its link, licence and sha256; `tools/fetch_sources.py` reads it like the other two manifests.

Installer files live under `software/files/`, which is gitignored. An installer is never
committed.

## Saving a user-fetched installer

An entry with `access: login` or `form` needs you (an account or a form):

1. `./run tools/fetch_sources.py` prints a to-do line with the page URL and the path to save to.
2. Open the page, sign in, download the full Windows installer (not a web stub), and save it at
   exactly the `file:` path in the manifest, for example
   `software/files/ti/pspice-for-ti-installer.zip`. If the real file name differs (an `.exe`),
   change the entry's `file:` to match.
3. Pin it: `./run tools/fetch_sources.py --record` writes the sha256 of any file that has none
   yet. Commit the manifest, not the installer.
4. `./run tools/fetch_sources.py --check` fails on a missing file or a hash mismatch.

`access: direct` entries (the LTspice installer) are downloaded by `fetch_sources.py` itself.
The image build downloads LTspice on its own and does not read this file; the entry is here for
the link and the hash.
