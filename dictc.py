#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @TODO: replace raw_input by cmd module
# @TODO: 在键盘中断时关闭线程
# @TODO: stardict is too slow
import subprocess
import tempfile
import os
import sys
import readline
import threading
from DictC import (
    BaseDict,
    DictCnDict,
    BingDict,
    StarDict,
    SpellCheck,
    External,
)
import unicodedata
import argparse


def width(string):
    return sum(1 + (unicodedata.east_asian_width(c) in "WF") for c in string)


class SoundThread(threading.Thread):
    def __init__(self, s):
        threading.Thread.__init__(self)
        self.s = s
        self._uri = ''

    def set_uri(self, uri):
        self._uri = uri
        self.s.do(self.uri)

    def get_uri(self):
        return self._uri

    def del_uri(self):
        del self._uri

    uri = property(get_uri, set_uri, del_uri, "Change src uri!")

    def run(self):
        pass


class FetchThread(threading.Thread):
    def __init__(self, keyword, args):
        threading.Thread.__init__(self)
        self.keyword = keyword
        self.args = args

    def run(self):
        global dict_instance
        if dict_instance is None:
            class_object = self.args['dict']
            dict_instance = class_object()
        dict_instance.setKeyword(self.keyword)
        status, content = dict_instance.getOutput()
        link = dict_instance.getLink(self.keyword)
        if status:
            content += "\n\n%s" % link
            output(content)
        else:
            print u'无解释'
            print link


class Completer(threading.Thread):
    def __init__(self, args):
        threading.Thread.__init__(self)
        self.prefix = None
        self.caches = {}
        self.format_string = "%s  %s"
        self.args = args

    def complete(self, prefix, index):
        if prefix in self.caches:
            try:
                w, t = self.caches[prefix][index]
                if not t.strip() or w.strip() == t.strip():
                    return w
                else:
                    return self.format_string % (w, t)
            except IndexError:
                return None
            except KeyError:
                return None
        if not prefix in self.caches or prefix != self.prefix:
            words = self.args['sugg'].fetchSuggestion(prefix)
            if not len(words):
                return None
            self.words = words
            # we have a new prefix!
            self.matching_words = [
                (w.encode('utf8'), t.encode('utf8')) for w, t in self.words
            ]
            widest = max([width(w.decode('utf8')) for w, t in
                          self.matching_words])
            self.matching_words = [
                ("%s%s" % (w, ' ' * (widest - width(w.decode('utf8')))), t) for
                w, t in self.matching_words]
            self.prefix = prefix
            self.caches[prefix] = self.matching_words
        try:
            w, t = self.matching_words[index]
            if not t.strip() or t.strip() == w.strip():
                return w
            else:
                return self.format_string % (w, t)
        except IndexError:
            return None

    def run(self, prefix, index):
        self.complete(prefix, index)


def paging(content, pager):
    f = tempfile.NamedTemporaryFile()
    f.write(content)
    f.flush()
    proc = subprocess.Popen("%s %s" % (pager, f.name), shell=True)
    proc.communicate()
    f.close()


def output(content):
    try:
        pager = os.environ.get('PAGER', 'more')
        paging(content, pager)
    except Exception:
        print content


def thread(keyword, args):
    f = FetchThread(keyword, args)
    f.setDaemon(True)
    f.start()
    f.join()


def get_parser():
    description = u'一个简单的在线查询单词小工具！'
    epilog = u"""
    当前版本：0.1.1

    主要功能：

    - 支持多个在线词典服务及星际译王词典
      bing      dict.bing.com.cn
      stardict  星际译王
    - 支持交互式模式下按<Tab>自动补全
      bing,dictcn(dict.cn),spellcheck(拼写检查),external(外部命令)
    - 发音支持
      需要 gstreamer 的 python 绑定，可以使用 yum/apt-get 安装。

    使用示例：

    $ %s hello
    直接查询 hello

    $ %s
    进入交互式模式，按 <CTRL-d> 退出！

    $ %s -d bing -c dictcn
    使用 dict.bing.com.cn 的在线翻译，dict.cn 来做查询时的自动补全！

    代码链接：

    https://github.com/grassofhust/dictc

    License:

    Beerware (If we meet some day, and you think
    this stuff is worth it, you can buy me a beer.)
    """ % (sys.argv[0], sys.argv[0], sys.argv[0])
    formatter_class = argparse.RawDescriptionHelpFormatter
    parser = argparse.ArgumentParser(description=description, epilog=epilog,
                                     formatter_class=formatter_class)
    parser.add_argument('-d', nargs='?',
                        help=u'词典（默认：bing）：%s ' %
                        ','.join(map(lambda d: d.metadata['id'],
                                     CLIAction.services)),
                        metavar=u'dictionary',
                        dest='dict',
                        action=CLIAction,
                        default=CLIAction.services[0],
                        choices=map(lambda d: d.metadata['id'],
                                    CLIAction.services),
                        )
    parser.add_argument('-c', nargs='?',
                        help=u'自动补全（默认：bing）：%s ' %
                        ','.join(map(lambda d: d.metadata['id'],
                                     CompletionAction.services)),
                        metavar=u'completion',
                        dest='sugg',
                        action=CompletionAction,
                        default=CompletionAction.services[0],
                        choices=map(lambda s: s.metadata['id'],
                                    CompletionAction.services),
                        )
    parser.add_argument('--nosound', help=u'禁用发音（默认启用）', dest='nosound',
                        action='store_true', default=False)
    parser.add_argument('-v', '--version', action='version',
                        version='%(prog)s 0.1.1')
    parser.add_argument('words', metavar='keyword or sentence', type=str,
                        nargs='*')
    return parser


def command_line_runner():
    parser = get_parser()
    args = vars(parser.parse_args())
    histfile = "%s/dictc_history_py" % tempfile.gettempdir()
    if (os.path.exists(histfile)):
        readline.read_history_file(histfile)
    hasSound = not args['nosound']
    if hasSound:
        try:
            from DictC.Sound import Sound  # @hack
            s = Sound()
            t = SoundThread(s)
            t.setDaemon(True)
            t.start()
        except ImportError:
            hasSound = False

    try:
        if not args['words']:
            print 'Press <Ctrl-D> or <Ctrl-C> to exit!'
            completer = Completer(args)
            readline.parse_and_bind("set show-all-if-ambiguous on")
            readline.parse_and_bind("set completion-ignore-case on")
            readline.parse_and_bind("set completion-map-case on")
            readline.parse_and_bind("set skip-completed-text on")
            readline.parse_and_bind("tab: complete")
            readline.set_completer(completer.complete)
            readline.set_completer_delims('')
            while True:
                line = raw_input('>> ')
                keyword = line.strip()
                if len(keyword):
                    if hasSound:
                        t.uri = BaseDict.soundUri(keyword)
                    thread(keyword, args)
        else:
            keyword = ' '.join(args['words'])
            readline.add_history(keyword)
            if hasSound:
                t.uri = BaseDict.soundUri(keyword)
            thread(keyword, args)
    except (EOFError, KeyboardInterrupt, SystemExit):
        pass

    readline.write_history_file(histfile)


if __name__ == "__main__":

    class CLIAction(argparse.Action):

        services = (BingDict, StarDict)

        def __init__(self, *args, **kwargs):
            super(CLIAction, self).__init__(*args, **kwargs)

        def __call__(self, parser, namespace, values, option_string=None):
            for service in self.services:
                if service.metadata['id'] == values:
                    return setattr(namespace, self.dest, service)

    class CompletionAction(CLIAction):

        services = (BingDict, DictCnDict, SpellCheck, External)

    dict_instance = None
    command_line_runner()


# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 textwidth=79
