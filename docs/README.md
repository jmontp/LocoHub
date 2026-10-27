# Plain HTML documentation

The public website is authored **HTML, CSS, and JavaScript** served by GitHub Pages.
The authoritative pages are `index.html` and the route directories under `docs/`.
There is no Markdown renderer, theme framework, CDN, or package installation needed
to build or serve the static website.

```bash
python3 docs/build.py --check
python3 docs/build.py --output site
python3 -m http.server 8000 --directory site
```

Open `http://localhost:8000/`. The builder uses only Python's standard library:
it checks local links and anchors, copies authored HTML and referenced assets,
and creates a plain JSON search index. A fresh output directory is required on
first use; subsequent builds recognize their own output manifest. No scientific
datasets outside `docs/` are read. Existing plot files are referenced and copied,
not duplicated into the authored source pages.

## Editing

- Edit HTML pages directly. Preserve page titles, the main landmark, navigation,
  relative URLs, and code example `data-language` attributes.
- Shared layout is styled by `stylesheets/site.css`; progressive enhancements
  for catalog filters, comparison, and search live in `javascripts/extra.js`.
- The catalog's HTML table remains usable without JavaScript. Comparison reads
  `datasets/comparison_data.json`; search reads the build-generated index.
- Keep the synthetic CSV and Parquet fixture equivalent. Tests execute the actual
  Python code embedded in `tutorials/index.html` and check both language examples.
- Add new pages with the same accessible shell. The builder discovers HTML routes
  automatically; it does not transform Markdown into HTML.

Markdown files and generated report snippets retained in this tree are historical
or internal audit references. They are **not published** and do not update the
HTML. `manage_dataset_documentation.py` maintains legacy Markdown/metadata outputs;
review corresponding HTML pages separately when catalog facts change. The retired
MkDocs configuration is archived at `legacy/docs/mkdocs.yml`.

## Checks and publication

```bash
python3 -m pip install -r requirements-curation.txt
python3 -m pytest tests/test_data_documentation.py
python3 docs/build.py --check
```

The dependency installation is for fixture/quality tests, not static publishing.
The documentation workflow validates pull requests against any base branch and
uploads a downloadable `locohub-html-preview` artifact. Production GitHub Pages
publication happens only from `main` after checks pass. The output includes
`.nojekyll`, and relative URLs preserve the `/LocoHub/` project base path.
