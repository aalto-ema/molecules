# Publish on GitHub

The repository is prepared for a public source upload: the README uses relative
links to committed screenshots, the MIT license is included, and CI checks code,
tests, and package builds. The canonical repository is
[aalto-ema/molecules](https://github.com/aalto-ema/molecules).

## Initial upload to a new repository

For a new fork or independent copy, create an empty public repository on GitHub. Leave its generated README, license,
and .gitignore options unchecked because these files already exist here.

From this project's root folder:

```sh
git init -b main
git add .
git diff --cached --stat
git diff --cached --check
git status --short
```

Review the staged files. `.gitignore` excludes `.venv`, caches, build output,
local editor/agent state, and common credential files. Keep personal drawings in
`drawings/` and local exports in `exports/`; those root folders are ignored.
The public examples and `docs/images/*.png` should be included.

Then commit and push, replacing `YOUR_GITHUB_REPOSITORY_URL` with the URL from
GitHub:

```sh
git commit -m "Initial public version of Molecules"
git remote add origin YOUR_GITHUB_REPOSITORY_URL
git push -u origin main
```

Use your normal GitHub authentication; do not put access tokens into tracked
files or remote URLs. An empty destination avoids conflicts with generated files.
If you already initialized Git or have a remote, inspect `git status` and
`git remote -v` before repeating these steps.

## Upload through the website

Upload the source folders `src`, `tests`, `docs`, `examples`, and `.github`,
along with the root files `README.md`, `LICENSE`, `pyproject.toml`, `run_app.py`,
`AGENTS.md`, `CONTRIBUTING.md`, `CHANGELOG.md`, `requirements-tested.txt`,
`.gitignore`, and `.gitattributes`. Preserve their folder structure. Do not upload
the entire working folder: browser uploads do not apply `.gitignore`.

The `.github` folder and dotfiles may be hidden in your file browser. Git is the
more reliable way to include them. Upload screenshots as normal files rather than
links to local paths or temporary URLs.

## After the first push

- Check that both README screenshots render and that the example links work.
- Inspect the first Actions run. CI is configured for three operating systems;
  local verification alone does not establish those hosted jobs have passed.
- Optionally add a repository description: “Python/PySide6 molecular drawing,
  reaction pathways, and guided mechanisms.” Suggested topics: `chemistry`,
  `rdkit`, `pyside6`, `chemical-drawing`, `reaction-mechanisms`.

## Build source packages

```sh
python -m pip install -e '.[dev]'
python -m build
```

`dist/` contains a source archive and an installable wheel. The source archive
includes the README screenshots, examples, tests, and project documentation.
Build artifacts are ignored by Git; publish them as release attachments only if
wanted. The wheel contains the app, packaged SVG asset, and MIT license, rather
than the whole documentation tree. A package build does not publish to PyPI.
