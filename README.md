# Why
This is a program for extract subtitles from `.mkv` files, finding some subtitles in opensubtitles (if this language not exist in a mkv file) and finally merging two subtitles with some language to a `.ass` file.
I use docker on my Rasberry Pi 3 because I have problems with file encoding (cyrillic characters in subtitles and file names).

# How to use
Use Python 3.11.18 and certifi 2026.10.19 or newer patched releases for the
October 2026 eMudhra CA incident. Python 3.8 and Alpine 3.15 no longer receive
security fixes. Rebuild with `--pull --no-cache` and recreate existing containers;
restarting an old image does not update its TLS verifier or certificate bundle.

The legacy `subliminal` and `iso-639` dependencies still need `pkg_resources`,
so runtime requirements retain `setuptools==81.0.0`. This is a compatibility
limit: [GHSA-xmj3-9gf7-h52w](https://github.com/advisories/GHSA-xmj3-9gf7-h52w)
affects legacy wheel installation on Windows, and
[GHSA-h35f-9h28-mq5c](https://github.com/advisories/GHSA-h35f-9h28-mq5c) affects
source-distribution creation on macOS. Neither operation is used by this Linux
container application. Use a separate, current build environment for packaging;
remove this pin when those legacy dependencies no longer need `pkg_resources`.

Build an image and a container.
There is an example `build.sh`
```
docker build -t sub-extr:latest .
docker create \
	--name sub-extr \
	-v /HOST_MOVIES_STORAGE_PATH:/MOVIES_STORAGE_PATH \
    sub-extr \
	/MOVIES_STORAGE_PATH/ \
	--merge-languages "ru-fr,ru-en" \
	--opensubtitles "username=XXX,password=YYY" \
	--languages "ru,en,fr"
```
And than run the container by crontab. Example
`run.sh`
```
docker start sub-extr
```

# Useful links

[matroska specifications](https://tools.ietf.org/id/draft-lhomme-cellar-matroska-04.html)
 
