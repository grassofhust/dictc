#!/usr/bin/env python
# -*- coding: utf-8 -*-
from distutils.core import setup


setup(name='dictc',
     version='0.1',
     url='https://github.com/grassofhust/dictc',
     author='kikyo',
     author_email='frederick.zou@gmail.com',
     py_modules=[],
     packages=['DictC'],
     scripts=['dictc'],
     license='Beerware',
     description=u'一个简单的在线查询单词小工具！',
     long_description=u"""主要功能：
- 支持多个在线词典服务
  qq    dict.qq.com
  bing  dict.bing.com.cn
- 支持交互式模式下按<Tab>自动补全
  qq/bing/dict(dict.cn)
- 发音支持
  需要 gstreamer 的 python 绑定，可以使用 yum/apt-get 安装。
     """
     )


# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 textwidth=79