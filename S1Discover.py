__author__ = 'eraserking'

import argparse
import os
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

    thread = args.thread
    first_page = download_page(create_url(thread, 1), 'get', download_proxy=thread_proxy)

    max_last_page_num = int(get_last_page_num(first_page))
    print('Page number of the last page in this thread is {}\n'.format(max_last_page_num))

    # If start page is not specified, go from page 1; otherwise the start page cannot be negative or exceed last page
    if not args.start_page:
        start_page = 1
    elif args.start_page <= 0:
        raise SyntaxError('Start page number cannot be less or equal to zero')
    elif args.start_page > max_last_page_num:
        raise SyntaxError('Start page number cannot exceed last page number')
    else:
        start_page = args.start_page

    # If end page is not specified, go to page last; otherwise the end page cannot be negative or exceed last page
    if not args.end_page:
        end_page = max_last_page_num
    elif args.end_page <= 0:
        raise SyntaxError('End page number cannot be less or equal to zero')
    elif args.end_page > max_last_page_num:
        raise SyntaxError('End page number cannot exceed last page number')
    else:
        end_page = args.end_page

    if start_page > end_page:
        raise SyntaxError('Start page number cannot be larger than last page number')

    all_posts = {}
    img_src = {}
    a_href = {}

    for page_num in range(start_page, end_page + 1):
        print('Parsing page {}'.format(page_num))
        current_page = download_page(create_url(thread, page_num), 'get', download_proxy=thread_proxy)
        all_posts_in_current_page, img_src_in_current_page, a_href_in_current_page = get_post_list(current_page)

        all_posts[page_num] = all_posts_in_current_page
        if len(img_src_in_current_page) > 0:
            img_src[page_num] = img_src_in_current_page
        if len(a_href_in_current_page) > 0:
            a_href[page_num] = a_href_in_current_page

    all_posts_file = open('thread_{}_posts_{}_{}.txt'.format(thread, start_page, end_page), 'w', errors='replace',
                          encoding='utf-8')
    write_to_file(all_posts_file, all_posts, False)
    all_posts_file.close()

    img_file = open('thread_{}_images_{}_{}.txt'.format(thread, start_page, end_page), 'w', errors='replace',
                    encoding='utf-8')
    write_to_file(img_file, img_src, True)
    img_file.close()

    a_file = open('thread_{}_links_{}_{}.txt'.format(thread, start_page, end_page), 'w', errors='replace',
                  encoding='utf-8')
    write_to_file(a_file, a_href, True)
    a_file.close()

    if args.download_image:
        failed_images = download_img(thread, img_src, img_proxy, args.only_for_failed_image)
        if (len(failed_images) > 0):
            a_file = open('thread_{}_img_failed_{}_{}.txt'.format(thread, start_page, end_page), 'w', errors='replace',
                          encoding='utf-8')
            a_file.writelines([x + '\n' for x in failed_images])
            a_file.close()


def write_to_file(file_handler, dictionary_to_write, include_post_num):
    for page_num in dictionary_to_write.keys():
        file_handler.write('>>>>> PAGE {}\n'.format(page_num))
        for post_num in sorted(dictionary_to_write[page_num].keys()):
            if include_post_num:
                file_handler.write('>>> POST {}\n'.format(post_num))
            file_handler.writelines(dictionary_to_write[page_num][post_num])


def download_img(thread, dictionary_to_download, img_proxy, only_for_failed_image):
    if not os.path.exists(str(thread)):
        os.makedirs(str(thread))

    failed_images = []

    for page_num in dictionary_to_download.keys():
        print('Download image(s) on page {}'.format(page_num))
        for post_num in sorted(dictionary_to_download[page_num].keys()):
            for img_seq in range(len(dictionary_to_download[page_num][post_num])):
                url = dictionary_to_download[page_num][post_num][img_seq].strip()
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

                # If only_for_failed_image is set, 1st without proxy and 2nd with proxy if 1st fails
                # If 2nd still fails, add to failed list
                if only_for_failed_image:
                    try:
                        req = requests.get(url, proxies={}, timeout=10)
                        if req.status_code == 200:
                            f = open(file_path, 'wb')
                            f.write(req.content)
                            f.close()

                    except Exception:
                        try:
                            req = requests.get(url, proxies=img_proxy, timeout=10)
                            if req.status_code == 200:
                                f = open(file_path, 'wb')
                                f.write(req.content)
                                f.close()

                        except Exception:
                            failed_images.append(url)

                # Just try once with proxy (if any)
                # If it fails, add to failed list
                else:
                    try:
                        req = requests.get(url, proxies=img_proxy, timeout=10)
                        if req.status_code == 200:
                            f = open(file_path, 'wb')
                            f.write(req.content)
                            f.close()

                    except Exception:
                        failed_images.append(url)

    return failed_images


def get_last_page_num(bs):
    try:
        page_indicator = bs.select('div[class="pg"]')[0]  # Select page bar
        last_page_node = page_indicator.select('a[class="last"]')[0]  # Select the link to the last page
        return last_page_node.text.replace('... ', '')
    # Note there may be no such last page link
    except IndexError:
        print('Cannot find the last page number.')
        sys.exit(1)


def get_post_list(bs):
    all_posts = {}
    img_src = {}
    a_href = {}

    # Select the post area
    post_area = bs.select('div[id="postlist"]')[0].select('table[class="plhin"]')
    for i, single_child_post in enumerate(post_area):

        # For the first post in every page, remove the first style node to remove '.pcb{margin-right:0}'.
        if i == 0:
            single_child_post.select('style')[0].decompose()

        try:
            author = 'UNKNOWN'
            author_nodes = single_child_post.select('a[class="xw1"]')
            if len(author_nodes) > 0:
                author = author_nodes[0].text

            date = 'UNKNOWN'
            date_nodes = single_child_post.select('div[class="pti"]')
            if len(date_nodes) > 0:
                date_nodes = date_nodes[0].select('em')
                if len(date_nodes) > 0:
                    date = date_nodes[0].text

            post_num = 1
            location_nodes = single_child_post.select('td[class="plc"]')
            if len(location_nodes) > 0:
                location_nodes = location_nodes[0].select('em')
                # For the first post, it's special - no text but an 'id' for this 'em' found
                # Just leave the default 1 and that's enough
                if len(location_nodes) > 0 and 'id' not in location_nodes[0].attrs:
                    post_num = int(location_nodes[0].text)

            post_title = '\n[#{}] {} {}\n'.format(post_num, author, date)

            content = ''
            content_nodes = single_child_post.select('div[class="pct"]')
            if len(content_nodes) > 0:
                content_node = content_nodes[0]

                # Show all quotes and then remove them all
                # So they won't appear in the post body any more
                quote_nodes = content_node.select('blockquote')
                if len(quote_nodes) > 0:
                    for quote_node in quote_nodes:
                        content = '-----\n' + quote_node.text + '\n-----\n'
                        quote_node.decompose()

                # Do not include emotion icons (which doesn't start with 'http')
                img_nodes = content_node.select('img')
                if len(img_nodes) > 0:
                    img_src[post_num] = [img_node.attrs['file'] + '\n' for img_node in img_nodes if
                                         'file' in img_node.attrs and img_node.attrs['file'].startswith('http')]
                    if len(img_src[post_num]) == 0:
                        del (img_src[post_num])

                # Do not include link as signature for the mobile app
                a_nodes = content_node.select('a')
                if len(a_nodes) > 0:
                    a_href[post_num] = [a_node.attrs['href'] + '\n' for a_node in a_nodes if
                                        a_node.attrs['href'].startswith('http') and not a_node.attrs[
                                                                                            'href'] in skipped_urls]
                    if len(a_href[post_num]) == 0:
                        del (a_href[post_num])

                content = content + content_node.text.strip()

                all_posts[post_num] = post_title + content + '\n'

        # If anything is wrong, just discard this post
        # I don't want to spend too much time on this
        except Exception:
            pass

    return all_posts, img_src, a_href


def download_page(url, method, data=None, download_proxy=None):
    if method == 'get':
        if data is not None:
            r = s.get(url, headers=default_header, data=data, proxies=download_proxy)
        else:
            r = s.get(url, headers=default_header, proxies=download_proxy)
    if method == 'post':
        if data is not None:
            r = s.post(url, headers=default_header, data=data, proxies=download_proxy)
        else:
            r = s.post(url, headers=default_header, proxies=download_proxy)

    return BeautifulSoup(r.content, 'html.parser', from_encoding='utf-8')


def create_url(thread, page):
    return 'http://bbs.saraba1st.com/2b/thread-{}-{}-1.html'.format(thread, page)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(fromfile_prefix_chars='@')
    parser.add_argument('thread', help='thread number', type=int)
    parser.add_argument('-p', '--proxy', dest='proxy', help='the proxy (HTTP/SOCKS5) to take')

    parser.add_argument('-s', '--start-page', dest='start_page', help='the page number to start with', type=int)
    parser.add_argument('-e', '--end-page', dest='end_page', help='the page number to end with', type=int)
    parser.add_argument('-d', '--download-image', dest='download_image', help='download images', default=False,
                        action='store_true')

    group = parser.add_mutually_exclusive_group()
    group.add_argument('-o', '--only-for-image', dest='only_for_image', help='only take proxy for downloading images',
                       default=False, action='store_true')
    group.add_argument('-f', '--only-for-failed-image', dest='only_for_failed_image',
                       help='only take proxy for failed downloading images',
                       default=False, action='store_true')
    main(parser.parse_args())
