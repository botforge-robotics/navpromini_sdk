"""MkDocs hooks.

The OpenAPI spec lives at the repo root, not in docs/, because it is the
source of truth for the API and belongs next to the code that serves it —
not buried in a documentation folder. But the published site needs to serve
it (the Redoc reference page fetches it, and integrators generate clients
from it), so it is copied into the build output at publish time rather than
duplicated in the repo.
"""

from __future__ import annotations

import os

from mkdocs.structure.files import File


def on_files(files, config):
    root = os.path.dirname(os.path.abspath(config['config_file_path']))
    if os.path.exists(os.path.join(root, 'openapi.yaml')):
        files.append(File(
            path='openapi.yaml',
            src_dir=root,
            dest_dir=config['site_dir'],
            use_directory_urls=config['use_directory_urls'],
        ))
    return files
