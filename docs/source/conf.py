# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
# 使用sphinx_rtd_theme主题
import sphinx_rtd_theme  # 在文件开头新增导入
# 支持MarkDown需导入
import recommonmark
from recommonmark.parser import CommonMarkParser
from recommonmark.transform import AutoStructify

# 新增检索代码的路径
import os
import sys
sys.path.insert(0, os.path.abspath('.'))
# 增加snakerpy的注释类型支持插件搜索路径
sys.path.append(
    os.path.join(os.path.dirname(__file__), os.path.pardir, 'ext')
)
# 子项目HiveNetCore的检索路径
sys.path.append(os.path.join(
    os.path.abspath(os.path.dirname(__file__)),
    os.path.pardir, os.path.pardir, 'HiveNetCore'
))
# 子项目HiveNetWebUtils的检索路径
sys.path.append(os.path.join(
    os.path.abspath(os.path.dirname(__file__)),
    os.path.pardir, os.path.pardir, 'HiveNetWebUtils'
))
# 子项目HiveNetSimpleSanic的检索路径
sys.path.append(os.path.join(
    os.path.abspath(os.path.dirname(__file__)),
    os.path.pardir, os.path.pardir, 'HiveNetSimpleSanic'
))
# 子项目HiveNetSimpleFlask的检索路径
sys.path.append(os.path.join(
    os.path.abspath(os.path.dirname(__file__)),
    os.path.pardir, os.path.pardir, 'HiveNetSimpleFlask'
))
# 子项目HiveNetGRpc的检索路径
sys.path.append(os.path.join(
    os.path.abspath(os.path.dirname(__file__)),
    os.path.pardir, os.path.pardir, 'HiveNetGRpc'
))
# 子项目HiveNetPipeline的检索路径
sys.path.append(os.path.join(
    os.path.abspath(os.path.dirname(__file__)),
    os.path.pardir, os.path.pardir, 'HiveNetPipeline'
))
# 子项目HiveNetPromptPlus的检索路径
sys.path.append(os.path.join(
    os.path.abspath(os.path.dirname(__file__)),
    os.path.pardir, os.path.pardir, 'HiveNetPromptPlus'
))
# 子项目HiveNetConsole的检索路径
sys.path.append(os.path.join(
    os.path.abspath(os.path.dirname(__file__)),
    os.path.pardir, os.path.pardir, 'HiveNetConsole'
))
# 子项目HiveNetFileTransfer的检索路径
sys.path.append(os.path.join(
    os.path.abspath(os.path.dirname(__file__)),
    os.path.pardir, os.path.pardir, 'HiveNetFileTransfer'
))


# -- Project information -----------------------------------------------------

project = 'HiveNetAssemble'
copyright = '2022, 黎慧剑'
author = '黎慧剑'

# The full version, including alpha/beta/rc tags
release = '0.1.0'


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.intersphinx',
    'sphinx.ext.coverage',
    'sphinx.ext.viewcode',
    'sphinx.ext.githubpages',
    'sphinx.ext.napoleon',
    'six',
    'napoleon_snakerpy',
    'recommonmark',
    'sphinx_markdown_tables'
]

# 增加Napoleon配置
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_snakerpy_docstring = True
napoleon_include_init_with_doc = True
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = False
napoleon_use_admonition_for_examples = False
napoleon_use_admonition_for_notes = False
napoleon_use_admonition_for_references = False
napoleon_use_ivar = False
napoleon_use_param = True
napoleon_use_rtype = True
napoleon_use_keyword = True
napoleon_custom_sections = None

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#
# This is also used if you do content translation via gettext catalogs.
# Usually you set "language" from the command line for these cases.
language = 'zh_CN'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
# html_theme = 'alabaster'
# 修改为
html_theme = 'sphinx_rtd_theme'
html_theme_path = [sphinx_rtd_theme.get_html_theme_path()]  # 新增

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# source_suffix = '.rst' 修改为支持md文档
source_suffix = ['.rst', '.md']

# 支持markdown文档
source_parsers = {
    '.md': 'recommonmark.parser.CommonMarkParser',
}

# app setup hook
github_doc_root = 'https://github.com/snakeclub/HiveNetAssemble/tree/main/docs/'


def setup(app):
    print('------------------启动会先执行-------------------')
    app.add_config_value('recommonmark_config', {
        'url_resolver': lambda url: github_doc_root + url,
        'auto_toc_tree_section': 'Contents',
        'enable_eval_rst': True,
    }, True)
    app.add_transform(AutoStructify)
