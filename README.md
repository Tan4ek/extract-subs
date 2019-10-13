# Why
This is a program for extract subtitles from `.mkv` files, finding some subtitles in opensubtitles (if this language not exist in a mkv file) and finally merging two subtitles with some language to a `.ass` file.
I use docker on my Rasberry Pi 3 because I have problems with file encoding (cyrillic characters in subtitles and file names).

# How to use
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
