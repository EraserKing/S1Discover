# S1Discover

This projects aims to create plain text file containing contents from all posts.
It should be much easier to read the file instead of scrolling and clicking next page in the browser all the time.

## Usage
`<python executable> S1Discover.py <thread> [-p <proxy> [-o|-f]] [-s <start page>] [-e <end page>] [-d]`

`thread`: The thread you want to download.

`-p`, `--proxy`: The proxy you want to access via for thread / image.
Usually it works for both accessing the posts and downloading images.

Both SOCKS5 and HTTP proxy are supported.

`-o`, `--only-for-image`: The proxy is only used for downloading images. Posts are directly accessed. A proxy must be specified first.

`-f`, `--only-for-failed-image`: The proxy is only used for downloading images which cannot be downloaded directly. Posts are directly accessed. A proxy must be specified first.

Images would be only download once if directly accessing works. If not, it would be accessed via the proxy again.

`-o` and `-f` cannot be used at the same time. Apparently you need to assign a proxy by `-p` when you use `-o` or `-f`.

`-s`, `--start-page`: The page number to start with. Must fall into 1 and the last page.

`-e`, `--end-page`: The page number to start with. Must fall into 1 and the last page.

If `-s` and `-e` are both assigned at the same time, `-s` must be equal or less than `-e`.

`-d`, `--download-image`: Download all images (except emotions) in the posts accessed.

## Quick Start
```
py -3 S1Discover.py 1296766 -d -p 127.0.0.1:1080 -f
```
The following actions are done (by 2017/02/22, the last page number of thread 1296766 is 372):
1. The content of all posts are saved into `thread_1296766_posts_1_372.txt`.
2. The URLs of the links mentioned in this thread are saved into `thread_1296766_links_1_372.txt`.
3. The images referred in this thread are saved into the folder `1296766`, and named after `<post number>-<sequence in the post>.<extension>`.
4. The image would be accessed directly first. If it fails, a second attempt would be performed via proxy `127.0.0.1:1080`.
5. If the second attempt also fails, the URL of the image is saved into `thread_1296766_img_failed_1_372.txt`

## Advanced
1. The image will not be downloaded again if you perform on the same thread / page again, unless the image is not downloaded before, or the size is 0.
2. The signuarture of user posts may contain links to different clients. They're just simply skipped, but there still may be something missing.

## Presequence
* Python 3
* Requests
* BeautifulSoup 4

## Known Issues
* If the total pages of the thread is too little, it fails. Read it manually!
* Every time it starts from the very beginning. No save-load support yet.
* No login support. So you cannot get thread with user right requirement.
* Downloading failed images may take a long time, and you cannot skip downloading any image. However as long as you wait long enough, it's still working.