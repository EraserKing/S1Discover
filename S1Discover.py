__author__ = 'eraserking'

import argparse
import os
import re
import sys

import requests
from bs4 import BeautifulSoup

default_header = {'Host': 'bbs.saraba1st.com',
                  'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/52.0.2743.116 Safari/537.36',
                  'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                  'Accept-Language': 'zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3',
                  'Accept-Encoding': 'gzip, deflate',
                  'Connection': 'keep-alive'}
skipped_urls = ['http://www.coolapk.com/apk/me.ykrank.s1next',
                'https://itunes.apple.com/cn/app/saralin/id1086444812',
                'https://github.com/ykrank/S1-Next/releases',
                'http://126.am/S1Nyan'
                'http://stage1.5j4m.com/?1.17',
                'http://stage1.5j4m.com/?1.19',
                'http://stage1.5j4m.com/?1.21',
                'http://stage1.5j4m.com/?1.22']

s = requests.session()


def main(args):
    if args.only_for_image and not args.proxy:
        raise SyntaxError('Cannot set image-only proxy without proxy set')
    if args.only_for_failed_image and not args.proxy:
        raise SyntaxError('Cannot set failed-image-only proxy without proxy set')

    img_proxy = {}
    thread_proxy = {}

    if args.proxy:
        img_proxy['http'] = args.proxy
        img_proxy['https'] = args.proxy

    if args.proxy and not args.only_for_image and not args.only_for_failed_image:
        thread_proxy['http'] = args.proxy
        thread_proxy['https'] = args.proxy

    first_page = download_single_page(create_url(args.thread, 1), 'get', download_proxy=thread_proxy)
    max_last_page_num = int(get_last_page_num(first_page))
    print('Page number of the last page in this thread is {}\n'.format(max_last_page_num))

    if not args.start_page:
        start_page = 1
    elif 0 < args.start_page <= max_last_page_num:
        start_page = args.start_page
    else:
        raise SyntaxError('Start page number must fall into range 1 ~ last page')

    if not args.end_page:
        end_page = max_last_page_num
    elif 0 < args.end_page <= max_last_page_num:
        end_page = args.end_page
    else:
        raise SyntaxError('End page number must fall into range 1 ~ last page')

    if start_page > end_page:
        raise SyntaxError('Start page number cannot be larger than last page number')

    all_posts = {}
    img_src = {}
    a_href = {}

    for page_num in range(start_page, end_page + 1):
        print('Parsing page {}'.format(page_num))
        current_page = download_single_page(create_url(args.thread, page_num), 'get', download_proxy=thread_proxy)
        all_posts_in_current_page, img_src_in_current_page, a_href_in_current_page = get_post_list(current_page)

        all_posts[page_num] = all_posts_in_current_page
        if len(img_src_in_current_page) > 0:
            img_src[page_num] = img_src_in_current_page
        if len(a_href_in_current_page) > 0:
            a_href[page_num] = a_href_in_current_page

    write_to_file('thread_{}_posts_{}_{}.txt'.format(args.thread, start_page, end_page), all_posts, first_page.title.text, False)
    write_to_file('thread_{}_images_{}_{}.txt'.format(args.thread, start_page, end_page), img_src, first_page.title.text, True)
    write_to_file('thread_{}_links_{}_{}.txt'.format(args.thread, start_page, end_page), a_href, first_page.title.text, True)

    if args.download_image:
        failed_images = download_images(args.thread, img_src, img_proxy, args.only_for_failed_image)
        if (len(failed_images) > 0):
            write_to_file('thread_{}_img_failed_{}_{}.txt'.format(args.thread, start_page, end_page), failed_images, first_page.title.text, True)


def write_to_file(file_name, dictionary_to_write, title, separate_element_in_post):
    file_handler = open(file_name, 'w', errors='replace', encoding='utf-8')
    file_handler.write(title + '\n')
    for page_num in dictionary_to_write.keys():
        file_handler.write('\n>> PAGE {}\n'.format(page_num))
        for post_num in sorted(dictionary_to_write[page_num].keys()):
            if separate_element_in_post:
                file_handler.write('>>>> POST {}\n'.format(post_num))
                file_handler.writelines([x + '\n' for x in dictionary_to_write[page_num][post_num]])
            else:
                file_handler.writelines(dictionary_to_write[page_num][post_num])
    file_handler.close()


def download_images(thread, dictionary_to_download, img_proxy, only_for_failed_image):
    if not os.path.exists(str(thread)):
        os.makedirs(str(thread))

    failed_images = {}

    for page_num in dictionary_to_download.keys():
        print('Download image(s) on page {}'.format(page_num))
        for post_num in sorted(dictionary_to_download[page_num].keys()):
            for img_seq in range(len(dictionary_to_download[page_num][post_num])):
                url = dictionary_to_download[page_num][post_num][img_seq]
                # Some images doesn't have extension in URL and it's assumed to be 'jpg'
                file_extension = url[url.rfind('/') + 1:]
                if file_extension.find('.') == -1:
                    file_extension = 'jpg'
                else:
                    file_extension = file_extension[file_extension.rfind('.') + 1:]

                # Some images may have extension like .jpg?1280x720
                if file_extension.find('?') != -1:
                    file_extension = file_extension[:file_extension.find('?')]

                # File name template = <thread>\<post> - <seq in post>.<extension>
                file_path = os.path.join(str(thread), '{}-{}.{}'.format(post_num, img_seq, file_extension))
                if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                    continue

                if only_for_failed_image:
                    final_success = download_single_image(url, file_path, {}) or download_single_image(url, file_path, img_proxy)
                else:
                    final_success = download_single_image(url, file_path, img_proxy)

                if not final_success:
                    if page_num not in failed_images:
                        failed_images[page_num] = {}
                    if post_num not in failed_images[page_num]:
                        failed_images[page_num][post_num] = []
                    failed_images[page_num][post_num].append(url)

    return failed_images


def download_single_image(url, file_path, proxy):
    try:
        req = requests.get(url, proxies=proxy, timeout=10)
        if req.status_code == 200:
            f = open(file_path, 'wb')
            f.write(req.content)
            f.close()
            return True
        return False

    except Exception:
        return False


def get_last_page_num(bs):
    try:
        page_indicator = bs.find('div', class_='pg').find('a', class_='last')
        return page_indicator.text.replace('... ', '')
    except AttributeError:
        print('Cannot find the last page number.')
        sys.exit(1)


def get_post_list(bs):
    all_posts = {}
    img_src = {}
    a_href = {}

    # Select the post area
    for i, single_child_post in enumerate(bs.find('div', id='postlist').find_all('table', class_='plhin')):
        # For the first post in every page, remove the first style node to remove '.pcb{margin-right:0}'.
        if i == 0:
            single_child_post.find('style').decompose()

        try:
            author = single_child_post.find('a', class_='xw1').text
            date = single_child_post.find('div', class_='pti').find('em').text
            post_num = int(single_child_post.find('a', id=re.compile('postnum\d+')).text.replace('#', '').replace('楼主', '1'))
            post_title = '\n[#{}] {} {}\n'.format(post_num, author, date)

            content = ''
            content_node = single_child_post.find('div', class_='pct')
            # Show all quotes and then remove them all, so they won't appear in the post body any more
            for quote_note in content_node.find_all('blockquote'):
                content = content + '-----\n' + quote_note.text + '\n-----\n'
                quote_note.decompose()

            # Do not include emotion icons (which doesn't start with 'http')
            img_src[post_num] = [x.attrs['file'] for x in single_child_post.find_all('img', file=re.compile('http.+'))]
            if not img_src[post_num]:
                del (img_src[post_num])

            # Do not include link as signature for the mobile app
            a_href[post_num] = [x.attrs['href'] for x in single_child_post.find_all('a', href=re.compile('http.+')) if x.attrs['href'] not in skipped_urls]
            if not a_href[post_num]:
                del (a_href[post_num])

            content = content + content_node.text.strip()
            all_posts[post_num] = post_title + content + '\n'

        # If anything is wrong, just discard this post - I don't want to spend too much time on this
        except Exception:
            pass

    return all_posts, img_src, a_href


def download_single_page(url, method, data=None, download_proxy=None):
    if method == 'get':
        r = s.get(url, headers=default_header, data=data, proxies=download_proxy)
    if method == 'post':
        r = s.post(url, headers=default_header, data=data, proxies=download_proxy)
    return BeautifulSoup(r.content, 'html.parser', from_encoding='utf-8')


def create_url(thread, page):
    return 'http://bbs.saraba1st.com/2b/thread-{}-{}-1.html'.format(thread, page)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(fromfile_prefix_chars='@')
    parser.add_argument('thread', help='thread number', type=int)
    parser.add_argument('-p', '--proxy', dest='proxy', help='the proxy (HTTP/SOCKS5) to take')

    parser.add_argument('-s', '--start-page', dest='start_page', help='the page number to start with', type=int)
    parser.add_argument('-e', '--end-page', dest='end_page', help='the page number to end with', type=int)
    parser.add_argument('-d', '--download-image', dest='download_image', help='download images', default=False, action='store_true')

    group = parser.add_mutually_exclusive_group()
    group.add_argument('-o', '--only-for-image', dest='only_for_image', help='only take proxy for downloading images', default=False, action='store_true')
    group.add_argument('-f', '--only-for-failed-image', dest='only_for_failed_image', help='only take proxy for failed downloading images', default=False,
                       action='store_true')
    main(parser.parse_args())
