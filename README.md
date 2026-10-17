# Boomber

Personal site for Boomber. GitHub Pages builds it with Jekyll. There is no separate build step.

The site currently has two entries: the Seamless Dimensions mod, and Waypoint on the projects page. Both lists grow by adding data, not by editing the layout.

## Add a release

1. Open `_data/releases/<mod-id>.yml`.
2. Add a new entry at the top. The page prints the list in that order, newest first.
3. Set `version`, `minecraft`, `loaders`, `requirements`, and `changelog`.
4. Put the jar in `files/<mod-id>/` and set `download` to `/files/<mod-id>/<filename>.jar`. A full URL is fine too.
5. Set `sha256` to that file's SHA-256, `file_size` to its size in bytes, and `date` to the day you published it (`YYYY-MM-DD`).
6. If the jar is not ready, leave `download`, `sha256`, `file_size`, and `date` empty. Do not invent them.

## Add a mod

1. Create `_data/mods/<mod-id>.yml` with `id`, `name`, `summary`, and `description`. Optional fields are `source`, `images`, and `upcoming`.
2. Create `_data/releases/<mod-id>.yml` with at least one release.
3. Create `mods/<mod-id>.html` with `layout: mod` and the same `mod_id`.

The mods page lists every file in `_data/mods`. Leave `source` empty when there should be no source link. The page links it only when the value is a URL. Add screenshots under `images`, each with `src` and `alt`. `upcoming` is for versions that are not releases yet. Each item needs `minecraft` and `loaders`.

## Add a project

Add an entry to `_data/projects.yml` with `name`, `url`, and `summary`. The projects page lists those entries in file order.

## GitHub Pages

In the repository, open Settings, then Pages. Under Build and deployment, set Source to **Deploy from a branch**. Choose branch `main` and folder `/ (root)`, then save.

The site is published at <https://oOBoomberOo.github.io>.

Do not add a CNAME file until boomber.xyz should point here.
